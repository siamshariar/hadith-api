#!/usr/bin/env python3
"""
Sync missing hadith translations from remote sources (Fawaz/HadeethEnc) into database
Usage:
  python scripts/sync_missing_translations.py --lang=bn --books=bukhari --limit=100 --dry-run
Options:
  --lang : comma-separated language codes (e.g., bn,en)
  --books: optional comma-separated book codes to restrict (e.g., bukhari,muslim)
  --limit: number of hadiths to process (default: 1000)
  --dry-run: don't write to DB, just fetch and print what would be inserted
    --source: comma-separated 'fawaz,hadeethenc,alquranbd'; default 'fawaz,hadeethenc,alquranbd'
"""

import argparse
import sys
import json
import time
from pprint import pprint
from datetime import datetime
import os
# Ensure scripts directory is in sys.path so we can import utils/config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Also add the parent scripts directory (project root scripts) to allow importing shared utils
parent_scripts = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
if os.path.isdir(parent_scripts):
    sys.path.insert(0, parent_scripts)
from utils import get_db_connection, fetch_hadith_data
from config import BOOK_CODE_MAP, LOCALIZATION_MAP, FAWAZ_HADITH_API_EDITIONS

# HadeethEnc API helper
HADEETHENC_API = 'https://hadeethenc.com/api/v1'

# alQuranBD API helper
ALQURAN_BD_API = 'https://alquranbd.com/api'

try:
    import requests
except Exception:
    print("Please ensure 'requests' package is installed (pip install requests)")
    sys.exit(1)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def api_get(url, params=None, timeout=10, silent=False):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 404:
            if not silent:
                log(f"[404] {url} {params}")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if not silent:
            log(f"[ERR] Fetch {url} failed: {e}")
        return None


def get_book_info_by_db_book_code(db_book_code):
    # `BOOK_CODE_MAP` keys match database book codes; return mapping if present
    if db_book_code in BOOK_CODE_MAP:
        return BOOK_CODE_MAP[db_book_code]
    # try slug conversion
    lower = db_book_code.lower()
    for bk, info in BOOK_CODE_MAP.items():
        if bk == lower or info.get('fawaz') and lower in info['fawaz'] or info.get('name_en') and lower in info['name_en'].lower():
            return info
    return None


def get_fawaz_edition_for_lang(book_info, lang_code):
    """Return a fawaz edition code for given language, e.g., 'ben-bukhari' or 'ara-bukhari'"""
    base_fawaz = book_info.get('fawaz', '')
    if not base_fawaz:
        return None
    if lang_code == 'ar':
        return base_fawaz
    # base fawaz is like 'ara-bukhari', replace 'ara-' with the lang prefix from config.LANG_TO_EDITION
    from config import LANG_TO_EDITION
    try:
        prefix = LANG_TO_EDITION.get(lang_code, lang_code)
        return base_fawaz.replace('ara-', f"{prefix}-")
    except Exception:
        return None


def fetch_translation_from_fawaz(book_info, hadith_number, lang_code, silent=False):
    edition = get_fawaz_edition_for_lang(book_info, lang_code)
    if not edition:
        if not silent:
            log(f"No fawaz edition for book {book_info.get('name_en')} for lang {lang_code}")
        return None
    # fetch by edition and hadith_number
    data = fetch_hadith_data(edition, int(hadith_number), silent=silent)
    if not data:
        return None

    # Determine translation text
    # Fawaz hadith object could have different keys; check 'text', 'translation' or 'translation_text'
    text = data.get('text') or data.get('translation') or data.get('translation_text') or data.get('hadeeth') or data.get('hadith')
    explanation = data.get('explanation') if isinstance(data.get('explanation'), str) else None
    hints = data.get('hints') or None
    references = data.get('references') or data.get('references_text') or data.get('hadith_references') or None
    # Normalize
    if text and isinstance(text, str) and len(text.strip()) > 0:
        return {
            'translation_text': text.strip(),
            'explanation': explanation,
            'hints': hints,
            'references': references
        }
    return None


def fetch_translation_from_hadeethenc(hadith_api_id, lang_code, book_code=None, hadith_number=None):
    """Fetch translation from HadeethEnc API.

    HadeethEnc: prefer to fetch by the hadith id in HadeethEnc (if available).
    Otherwise try the book/hadith_number book-based route where supported.
    """
    url = None
    params = None

    # When we have a HadeethEnc ID (our DB hadith id may match HadeethEnc id if synced)
    if hadith_api_id:
        url = f"{HADEETHENC_API}/hadeeths/one"
        params = {'id': hadith_api_id, 'language': lang_code}
    elif book_code and hadith_number:
        # Some HadeethEnc endpoints support book & hadith number based translation retrieval
        url = f"{HADEETHENC_API}/books/{book_code}/hadiths/{hadith_number}/translations/{lang_code}"
        params = None
    else:
        return None

    data = api_get(url, params=params, silent=True)
    if not data:
        return None
    if 'hadeeth' in data and data['hadeeth']:
        text = data['hadeeth']
        explanation = data.get('explanation')
        hints = data.get('hints')
        references = data.get('references') or data.get('references_text')
        return {
            'translation_text': text,
            'explanation': explanation,
            'hints': hints,
            'references': references
        }
    return None


def fetch_translation_from_alquranbd(book_code, chapter_no, hadith_number, lang_code):
    """Fetch translation from alquranbd API by book, chapter and hadith number.
    The alquranbd API returns hadiths per chapter; this helper tries the chapter endpoint
    and then paginated pages if available.
    """
    try:
        if not book_code or not chapter_no:
            return None

        # Try to fetch the chapter hadith list directly
        url = f"{ALQURAN_BD_API}/hadith/{book_code}/{chapter_no}"
        data = api_get(url, silent=True)
        if data and isinstance(data, list):
            for h in data:
                # Common keys: 'hadithNo', 'hadith_number', 'hadithNo', 'id'
                if str(h.get('hadithNo') or h.get('hadith_number') or h.get('id')).strip() == str(hadith_number).strip():
                    text = h.get('hadithBengali') or h.get('hadithEnglish') or h.get('hadith') or h.get('hadeeth')
                    if text and len(str(text).strip()) > 0:
                        return {
                            'translation_text': str(text).strip(),
                            'explanation': None,
                            'hints': None,
                            'references': None
                        }

        # Fallback to paginated pages if API has pages endpoint
        pages_url = f"{ALQURAN_BD_API}/hadith/{book_code}/{chapter_no}/pages"
        pages = api_get(pages_url, silent=True)
        if pages and isinstance(pages, list):
            for p in pages:
                page_no = p.get('pageNo') or p.get('page')
                # Use the same base path (ALQURAN_BD_API already points to /api)
                page_url = f"{ALQURAN_BD_API}/hadith/{book_code}/{chapter_no}/{page_no}"
                page_data = api_get(page_url, silent=True)
                if not page_data or not isinstance(page_data, list):
                    continue
                for h in page_data:
                    if str(h.get('hadithNo') or h.get('hadith_number') or h.get('id')).strip() == str(hadith_number).strip():
                        text = h.get('hadithBengali') or h.get('hadithEnglish') or h.get('hadith') or h.get('hadeeth')
                        if text and len(str(text).strip()) > 0:
                            return {
                                'translation_text': str(text).strip(),
                                'explanation': None,
                                'hints': None,
                                'references': None
                            }
    except Exception as e:
        log(f"Error fetching alquranbd: {e}")
    return None


def main():
    parser = argparse.ArgumentParser(description='Sync missing translations for all hadiths')
    parser.add_argument('--lang', type=str, default='en', help='Comma separated languages to sync, e.g., bn,en')
    parser.add_argument('--languages', type=str, default=None, help='Alias for --lang (comma-separated languages)')
    parser.add_argument('--books', type=str, default=None, help='Optional comma separated book codes to filter')
    parser.add_argument('--limit', type=int, default=1000, help='Max number of hadiths to process per run (0==all)')
    parser.add_argument('--batch-size', type=int, default=500, help='Number of hadiths to process per database batch')
    parser.add_argument('--dry-run', action='store_true', help='Do not write to DB')
    parser.add_argument('--import-file', type=str, default=None, help='Optional JSON/NDJSON file with translations to prioritize')
    parser.add_argument('--sample', type=int, default=None, help='Take only the first N missing hadiths for quick tests')
    parser.add_argument('--source', type=str, default='fawaz,hadeethenc,alquranbd', help='Source priority list: comma separated fawaz,hadeethenc,alquranbd')
    args = parser.parse_args()

    # Support --languages alias
    lang_arg = args.languages if args.languages else args.lang
    languages = [l.strip() for l in lang_arg.split(',') if l.strip()]
    # Support --lang=all for all languages in LOCALIZATION_MAP
    if len(languages) == 1 and languages[0].lower() == 'all':
        languages = list(LOCALIZATION_MAP.keys())
    book_filters = [b.strip() for b in args.books.split(',')] if args.books else None
    sources = [s.strip() for s in args.source.split(',')]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Build list of hadiths missing translation for langs
    report_summary = {
        'run_started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'languages': {}
    }

    for lang in languages:
        log(f"Processing language: {lang}")

        # Map localization_id from config if exists
        localization_id = LOCALIZATION_MAP.get(lang, {}).get('id', None)
        if localization_id is None:
            log(f"Warning: No localization id configured in LOCALIZATION_MAP for '{lang}', using 0")
            localization_id = 0

        # Build SQL selecting hadiths missing translation for `lang`
        sql = "SELECT h.id, h.book_id, h.hadith_number, b.code AS book_code, b.slug AS book_slug, c.chapter_no FROM hadiths h JOIN books b ON h.book_id = b.id JOIN chapters c ON h.chapter_id = c.id WHERE NOT EXISTS (SELECT 1 FROM hadith_translations t WHERE t.hadith_id = h.id AND t.localization_code = %s)"
        params = [lang]
        if book_filters:
            sql += " AND b.code IN ({})".format(','.join(['%s'] * len(book_filters)))
            params += book_filters
        sql += " ORDER BY h.id ASC"
        # If limit>0, we'll fetch up to limit using batch loop, otherwise process all

        # Batch processing - run SQL with LIMIT OFFSET using args.batch_size
        offset = 0
        total_missing = 0
        rows = []
        fetch_limit = args.limit if args.limit and args.limit > 0 else None
        while True:
            batch_sql = sql + " LIMIT %s OFFSET %s"
            batch_params = params + [args.batch_size, offset]
            cursor.execute(batch_sql, batch_params)
            batch_rows = cursor.fetchall()
            if not batch_rows:
                break
            rows.extend(batch_rows)
            total_missing += len(batch_rows)
            offset += args.batch_size
            # Stop if fetch_limit reached
            if fetch_limit and total_missing >= fetch_limit:
                break

        log(f"Found {len(rows)} hadiths missing translations for {lang}")

        count_processed = 0
        count_imported = 0
        count_updated = 0
        count_skipped = 0

        # Optionally reduce rows for sample/testing
        if args.sample and isinstance(args.sample, int) and args.sample > 0:
            rows = rows[:args.sample]

        for r in rows:
            hadith_id = r['id']
            book_code = r['book_code']
            hadith_number = r['hadith_number']
            book_info = get_book_info_by_db_book_code(book_code)
            if not book_info:
                log(f"No book mapping found for book code {book_code}")
                count_skipped += 1
                continue

            # We'll try sources in priority order
            # First check local import JSON file if provided; this takes precedence
            if args.import_file:
                # attempt to load once and cache
                if 'local_imports' not in locals():
                    local_imports = {}
                    path = os.path.join(os.getcwd(), args.import_file)
                    if os.path.exists(path):
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                filedata = json.load(f)
                            # Normalize different export shapes
                            def walk_and_extract(node):
                                # Find hadith objects with 'id' and 'translation' keys
                                if isinstance(node, dict):
                                    if node.get('id') and node.get('translation') and isinstance(node.get('translation'), dict):
                                        tid = str(node.get('id'))
                                        local_imports[tid] = node.get('translation')
                                    else:
                                        for v in node.values():
                                            walk_and_extract(v)
                                elif isinstance(node, list):
                                    for it in node:
                                        walk_and_extract(it)
                            walk_and_extract(filedata)
                        except Exception as e:
                            print(f"[import-file] failed to load {args.import_file}: {e}")
                # If we have a translation in local_imports, use it
                hit = local_imports.get(str(hadith_id)) if 'local_imports' in locals() else None
                if hit:
                    # hit is a translation object -> convert to our format
                    translation = {
                        'translation_text': hit.get('translation_text') or hit.get('translation') or hit.get('text') or hit.get('hadith'),
                        'explanation': hit.get('explanation') or None,
                        'hints': hit.get('hints') or None,
                        'references': hit.get('references') or None
                    }
                    if translation['translation_text']:
                        log(f"Using local import-file translation for hadith {hadith_id}")
                    else:
                        translation = None
            translation = None
            # For Fawaz, we must convert hadith_number to numeric if possible
            for src in sources:
                if src == 'fawaz':
                    translation = fetch_translation_from_fawaz(book_info, hadith_number, lang, silent=True)
                    if translation:
                        log(f"Fetched translation from Fawaz for hadith {hadith_id} (book {book_code} #{hadith_number})")
                        break
                elif src == 'hadeethenc':
                    # HadeethEnc can try by hadith id, or by book/hadith number
                    translation = fetch_translation_from_hadeethenc(hadith_id, lang, book_code=book_code, hadith_number=hadith_number)
                    if translation:
                        log(f"Fetched translation from HadeethEnc for local hadith {hadith_id}")
                        break
                elif src == 'alquranbd':
                    # Attempt to fetch from alquranbd API using (book, chapter, hadith number)
                    chapter_no = r.get('chapter_no')
                    # Resolve book code for alquranbd from BOOK_CODE_MAP
                    mapped = get_book_info_by_db_book_code(book_code)
                    alquran_book_key = None
                    if mapped:
                        alquran_book_key = mapped.get('alquran_bd') or mapped.get('fawaz') or book_code
                    translation = fetch_translation_from_alquranbd(alquran_book_key, chapter_no, hadith_number, lang)
                    if translation:
                        log(f"Fetched translation from alquranbd for hadith {hadith_id} (book {book_code} chapter {chapter_no} #{hadith_number})")
                        break

            if not translation:
                log(f"No translation found for hadith {hadith_id} book {book_code} #{hadith_number}")
                count_skipped += 1
                continue

            # Build data
            trans_text = translation.get('translation_text')
            explanation = translation.get('explanation')
            hints = translation.get('hints')
            hints_json = json.dumps(hints, ensure_ascii=False) if hints else None
            # Skip empty translations
            if not trans_text or not isinstance(trans_text, str) or not trans_text.strip():
                log(f"Skipping hadith {hadith_id} because translation text is empty")
                count_skipped += 1
                continue
            if args.dry_run:
                pprint({
                    'hadith_id': hadith_id,
                    'localization_id': localization_id,
                    'localization_code': lang,
                    'translation_text': trans_text[:200] if trans_text else None,
                    'explanation': explanation[:200] if explanation else None
                })
                count_processed += 1
                continue

            try:
                # Insert into hadith_translations
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("SELECT id FROM hadith_translations WHERE hadith_id = %s AND localization_code = %s", (hadith_id, lang))
                exists = cursor.fetchone()
                if exists:
                    # Update
                    cursor.execute("UPDATE hadith_translations SET translation_text = %s, explanation = %s, hints = %s, updated_at = %s WHERE id = %s",
                                   (trans_text, explanation, hints_json, now, exists['id']))
                    log(f"Updated translation for hadith {hadith_id} lang {lang}")
                    count_updated += 1
                else:
                    if not localization_id:
                        localization_id = LOCALIZATION_MAP.get(lang, {}).get('id', 0)
                    cursor.execute("INSERT INTO hadith_translations (hadith_id, localization_id, localization_code, translation_text, explanation, hints, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                                   (hadith_id, localization_id, lang, trans_text, explanation, hints_json, now, now))
                    log(f"Inserted translation for hadith {hadith_id} lang {lang}")
                    count_imported += 1
                # Also try to insert reference translation if available (not supported for all sources)
                # If the remote has 'references' we store in hadith_reference_translations
                if translation and ('references' in translation and translation['references']):
                    refs_json = json.dumps(translation['references'], ensure_ascii=False)
                    cursor.execute("INSERT INTO hadith_reference_translations (hadith_id, localization_code, references_text, created_at, updated_at) VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE references_text = VALUES(references_text), updated_at = VALUES(updated_at)",
                                   (hadith_id, lang, refs_json, now, now))

                conn.commit()
            except Exception as e:
                log(f"DB error inserting translation for hadith {hadith_id} lang {lang}: {e}")
                conn.rollback()

            count_processed += 1
            time.sleep(0.05)
        log(f"Done language {lang}: processed {count_processed}, imported {count_imported}, updated {count_updated}")

        report_summary['languages'][lang] = {
            'processed': count_processed,
            'inserted': count_imported,
            'updated': count_updated,
            'skipped': count_skipped
        }

    cursor.close()
    conn.close()

    # Write summary report
    try:
        report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sync_reports')
        os.makedirs(report_path, exist_ok=True)
        report_file = os.path.join(report_path, f"sync_missing_translations_report_{int(time.time())}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_summary, f, ensure_ascii=False, indent=2)
        log(f"Wrote summary report to {report_file}")
    except Exception as e:
        log(f"Failed to write summary report: {e}")


if __name__ == '__main__':
    main()
