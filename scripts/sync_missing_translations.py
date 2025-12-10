#!/usr/bin/env python3
"""
Sync missing hadith translations from Fawaz hadith API into local DB.

Usage examples:
  # Dry-run report missing counts for bn and en
  python scripts/sync_missing_translations.py --languages bn,en --dry-run

  # Import missing translations for bn (safe sample of 100)
  python scripts/sync_missing_translations.py --languages bn --sample 100

Features:
- Computes missing hadith_translations per language
- Optionally fetches translation from Fawaz editions using utils.fetch_hadith_data
- Attempts to resolve hadith by id, or by book+hadith_number
- Supports batching, sample mode, dry-run, verbose logging
- Writes translations into hadith_translations with localization_id when mapping exists
"""
import argparse
import sys
import time
import json
from typing import List, Optional

from config import BOOK_CODE_MAP, LOCALIZATION_MAP, FAWAZ_HADITH_API_EDITIONS
from utils import get_db_connection, fetch_hadith_data, clean_text
import os


def load_local_json_index(lang: str):
    """Search common local JSON files and index translations by hadith id and by book+hadith_number.
    Returns two dicts: by_id, by_book_number
    """
    candidates = [
        'test_bengali_output.json',
        'temp_bn.json',
        'missing_bn_all.json',
        'test_arabic_output.json',
        'test_en_with_ref.json'
    ]
    by_id = {}
    by_book = {}

    def walk_node(node, parent_book=None):
        if isinstance(node, dict):
            # if node has translation fields keyed by localization code or 'translation'
            # Try to normalize
            if 'id' in node:
                hid = node.get('id')
                trans = None
                if 'translation' in node and isinstance(node['translation'], dict):
                    t = node['translation']
                    # if translation per language
                    if isinstance(t.get('translation_text'), str):
                        trans = t.get('translation_text')
                    elif isinstance(t.get('text'), str):
                        trans = t.get('text')
                # Also try direct fields
                if not trans:
                    trans = node.get('translation_text') or node.get('text') or node.get('translation')

                # If nested localized translation map exists
                if isinstance(trans, dict) and lang in trans:
                    trans = trans.get(lang)

                if trans and isinstance(trans, str) and hid:
                    by_id[int(hid)] = clean_text(trans)

            # If node contains hadiths array, recurse
            for k, v in node.items():
                # capture book context if present
                if k == 'book' and isinstance(v, dict):
                    parent_book = v.get('code') or v.get('slug') or parent_book
                walk_node(v, parent_book=parent_book)

        elif isinstance(node, list):
            for item in node:
                walk_node(item, parent_book=parent_book)

    for fn in candidates:
        path = os.path.join(os.getcwd(), fn)
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            walk_node(data)
        except Exception:
            # ignore parse errors
            continue

    return by_id, by_book


def parse_args():
    p = argparse.ArgumentParser(description='Sync missing translations from Fawaz API')
    p.add_argument('--languages', type=str, required=True,
                   help='Comma-separated language codes to sync, e.g. bn,en,ur')
    p.add_argument('--books', type=str, default=None,
                   help='Comma-separated book codes to limit (e.g. bukhari,muslim)')
    p.add_argument('--import-file', type=str, default=None,
                   help='Optional local JSON file to import translations from')
    p.add_argument('--dry-run', action='store_true', help='Only report missing counts, do not insert')
    p.add_argument('--overwrite', action='store_true', help='Overwrite existing translations (process even when translations exist)')
    p.add_argument('--confirm', action='store_true', help='Confirm destructive action (required with --overwrite)')
    p.add_argument('--sample', type=int, default=None, help='Only process first N missing items')
    p.add_argument('--limit', type=int, default=1000, help='Batch limit when computing missing ids')
    p.add_argument('--sleep', type=float, default=0.15, help='Delay between remote requests (seconds)')
    p.add_argument('--verbose', action='store_true')
    return p.parse_args()


def get_missing_hadith_ids(cursor, lang: str, book_ids: Optional[List[int]] = None, limit: Optional[int] = None, overwrite: bool = False):
    """Return list of hadith ids that have no translation for `lang`.
    Optionally filter to hadiths in given book_ids.
    """
    params = []
    # If overwrite is True, fetch all hadith ids in the scope (we will update them after fetching translations)
    if overwrite:
        sql = (
            "SELECT h.id, h.book_id, h.hadith_number FROM hadiths h "
            "WHERE 1=1"
        )
    else:
        sql = (
            "SELECT h.id, h.book_id, h.hadith_number FROM hadiths h "
            "LEFT JOIN hadith_translations t ON h.id = t.hadith_id AND t.localization_code = %s "
            "WHERE t.id IS NULL"
        )
    if not overwrite:
        params.append(lang)

    if book_ids:
        sql += " AND h.book_id IN ({})".format(','.join(['%s'] * len(book_ids)))
        params.extend(book_ids)

    sql += " ORDER BY h.id"
    if limit:
        sql += " LIMIT %s"
        params.append(limit)

    cursor.execute(sql, tuple(params))
    return cursor.fetchall()  # rows of (id, book_id, hadith_number)


def hadith_exists(cursor, hadith_id: int) -> bool:
    cursor.execute("SELECT 1 FROM hadiths WHERE id = %s LIMIT 1", (hadith_id,))
    return cursor.fetchone() is not None


def find_hadith_by_book_number(cursor, book_id: int, hadith_number) -> Optional[int]:
    cursor.execute("SELECT id FROM hadiths WHERE book_id = %s AND hadith_number = %s LIMIT 1",
                   (book_id, hadith_number))
    row = cursor.fetchone()
    return row[0] if row else None


def upsert_translation(cursor, hadith_id: int, lang: str, text: str, localization_id: Optional[int]):
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # Check existing
    cursor.execute("SELECT id FROM hadith_translations WHERE hadith_id = %s AND localization_code = %s",
                   (hadith_id, lang))
    row = cursor.fetchone()
    if row:
        tid = row[0]
        cursor.execute(
            "UPDATE hadith_translations SET translation_text = %s, updated_at = %s WHERE id = %s",
            (text, now, tid)
        )
        return 'updated'
    else:
        cols = ['hadith_id', 'localization_code', 'translation_text', 'created_at', 'updated_at']
        vals = [hadith_id, lang, text, now, now]
        if localization_id:
            cols.insert(1, 'localization_id')
            vals.insert(1, localization_id)
        placeholders = ','.join(['%s'] * len(cols))
        sql = f"INSERT INTO hadith_translations ({','.join(cols)}) VALUES ({placeholders})"
        cursor.execute(sql, tuple(vals))
        return 'inserted'


def main():
    args = parse_args()
    langs = [l.strip() for l in args.languages.split(',') if l.strip()]
    books = [b.strip() for b in args.books.split(',')] if args.books else None

    # Resolve book ids if books specified
    book_ids = None
    if books:
        # Map codes to ids via DB
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, code FROM books WHERE code IN ({})".format(','.join(['%s'] * len(books))), tuple(books))
        rows = cur.fetchall()
        code_to_id = {r[1]: r[0] for r in rows}
        book_ids = [code_to_id[b] for b in books if b in code_to_id]
        conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()

    total_to_process = 0
    per_lang_missing = {}

    # Step 1: detect missing translations per language
    for lang in langs:
        missing_rows = get_missing_hadith_ids(cursor, lang, book_ids=book_ids, limit=args.limit, overwrite=args.overwrite)
        per_lang_missing[lang] = missing_rows
        total_to_process += len(missing_rows)
        if args.verbose:
            print(f"[detect] language={lang} missing_count={len(missing_rows)}")

    print(f"Detected {total_to_process} missing translations across languages: " + ', '.join([f"{k}={len(v)}" for k, v in per_lang_missing.items()]))

    if args.dry_run or total_to_process == 0:
        print("Dry-run mode or no missing items — exiting.")
        cursor.close()
        conn.close()
        return

    # Safety: require explicit confirmation when overwrite is used to avoid accidental mass updates
    if args.overwrite and not args.confirm:
        print("--overwrite requested but --confirm missing. Add --confirm to proceed with destructive update")
        cursor.close()
        conn.close()
        return

    processed = 0
    inserted = 0
    updated = 0
    skipped = 0

    # Build local index of translations for quick lookup
    local_indexes = {}
    for lang_code in langs:
        # load indexed local files plus any provided import-file
        by_id, by_book = load_local_json_index(lang_code)
        # if user provided an import-file, try to load and merge
        if args.import_file:
            path = os.path.join(os.getcwd(), args.import_file)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # reuse walk logic by dumping to temp and walking
                    def safe_walk(node):
                        if isinstance(node, dict):
                            hid = node.get('id')
                            trans = None
                            if 'translation' in node and isinstance(node['translation'], dict):
                                t = node['translation']
                                trans = t.get('translation_text') or t.get('text')
                            if not trans:
                                trans = node.get('translation_text') or node.get('text') or node.get('translation')
                            if isinstance(trans, dict) and lang_code in trans:
                                trans = trans.get(lang_code)
                            if trans and hid:
                                by_id[int(hid)] = clean_text(trans)
                            for v in node.values():
                                safe_walk(v)
                        elif isinstance(node, list):
                            for item in node:
                                safe_walk(item)
                    safe_walk(data)
                except Exception:
                    if args.verbose:
                        print(f"[import-file] failed to parse {args.import_file}")
        local_indexes[lang_code] = (by_id, by_book)

    # Main loop: for each lang and each missing hadith, fetch and insert
    for lang, rows in per_lang_missing.items():
        localization_id = LOCALIZATION_MAP.get(lang, {}).get('id') if lang in LOCALIZATION_MAP else None
        # Decide edition prefix from BOOK_CODE_MAP mapping
        for row in rows:
            if args.sample and processed >= args.sample:
                break
            hadith_id, book_id, hadith_number = row

            # Try to fetch translation by hadith id from Fawaz: edition detection requires edition name
            # Find book code from DB
            cursor.execute("SELECT code FROM books WHERE id = %s LIMIT 1", (book_id,))
            bcode_row = cursor.fetchone()
            book_code = bcode_row[0] if bcode_row else None

            # If book code maps in BOOK_CODE_MAP, build edition code
            fawaz_edition = None
            if book_code and book_code in BOOK_CODE_MAP:
                fawaz_base = BOOK_CODE_MAP[book_code].get('fawaz')
                if fawaz_base:
                    # Replace prefix (ara-) with language prefix
                    lang_prefix = lang if len(lang) == 3 else (lang if len(lang) == 2 else lang)
                    # Map 2-letter to LANG_TO_EDITION via config if available
                    # FAWAZ edition format in config: 'ara-bukhari' etc. We'll replace 'ara' with code mapping where possible.
                    # Simpler: use the stored fawaz base and replace leading 'ara' with LANG code mapping from config module if exists
                    try:
                        from config import LANG_TO_EDITION
                        prefix = LANG_TO_EDITION.get(lang, 'eng')
                        fawaz_edition = fawaz_base.replace('ara', prefix)
                    except Exception:
                        fawaz_edition = fawaz_base

            # First try local index (faster and offline)
            translation_text = None
            hadith_data = None
            local_by_id, local_by_book = local_indexes.get(lang, ({}, {}))
            if int(hadith_id) in local_by_id:
                translation_text = local_by_id[int(hadith_id)]
                if args.verbose:
                    print(f"[local] found translation by id for hadith {hadith_id} lang={lang}")

            # Also try book+number lookup in local files
            if not translation_text and book_code and (book_code, str(hadith_number)) in local_by_book:
                translation_text = local_by_book[(book_code, str(hadith_number))]
                if args.verbose:
                    print(f"[local] found translation by book+number for {book_code}#{hadith_number} lang={lang}")

            # Build candidate URLs and try remote fetch if not found locally
            if not translation_text:
                # Try multiple edition prefixes if fawaz_base exists
                tried_editions = []
                if fawaz_base:
                    try:
                        from config import LANG_TO_EDITION
                        # try the exact mapped prefix, then fallback to 'ben'/'eng'/'ara'
                        prefixes = [LANG_TO_EDITION.get(lang, ''), lang, 'ben', 'eng', 'ara']
                        for pref in prefixes:
                            if not pref:
                                continue
                            candidate = fawaz_base.replace('ara', pref)
                            if candidate in tried_editions:
                                continue
                            tried_editions.append(candidate)
                            if args.verbose:
                                print(f"[fetch] trying edition {candidate} for {book_code} #{hadith_number}")
                            hadith_data = fetch_hadith_data(candidate, hadith_number, silent=not args.verbose)
                            if hadith_data:
                                break
                    except Exception:
                        # Last resort: try fawaz_base as-is
                        try:
                            hadith_data = fetch_hadith_data(fawaz_base, hadith_number, silent=not args.verbose)
                        except Exception:
                            hadith_data = None

            # If no data and hadith id exists in local DB, try fetching by global id from some sources (skip for now)
            if not hadith_data:
                # Could try fetching by hadith_id via other endpoints, but Fawaz editions are by book+number.
                # As fallback, skip insertion.
                if args.verbose:
                    print(f"[fetch] no data for book={book_code} hadith_number={hadith_number} lang={lang}")
                skipped += 1
                processed += 1
                time.sleep(args.sleep)
                continue

            # Extract translation text fields depending on structure
            # If translation_text was populated from local index, use it
            if not translation_text and isinstance(hadith_data, dict):
                text = hadith_data.get('text') or hadith_data.get('translation') or hadith_data.get('content') or ''
                # If translation is nested dict, try common keys
                if isinstance(text, dict):
                    text = text.get('translation_text') or text.get('text') or ''
                text = clean_text(text)
                if not text:
                    if args.verbose:
                        print(f"[skip] empty text for {book_code} #{hadith_number} lang={lang}")
                    skipped += 1
                    processed += 1
                    time.sleep(args.sleep)
                    continue
                translation_text = text

            # Ensure we have a hadith_id in our DB; if hadith_id doesn't exist (rare) try to resolve by book+number
            if not hadith_exists(cursor, hadith_id):
                resolved = find_hadith_by_book_number(cursor, book_id, hadith_number)
                if resolved:
                    hadith_id = resolved
                else:
                    if args.verbose:
                        print(f"[resolve] cannot resolve local hadith id for book={book_code} number={hadith_number}")
                    skipped += 1
                    processed += 1
                    time.sleep(args.sleep)
                    continue

            # Upsert into DB
            try:
                result = upsert_translation(cursor, hadith_id, lang, translation_text, localization_id)
                if result == 'inserted':
                    inserted += 1
                else:
                    updated += 1
                conn.commit()
                if args.verbose:
                    print(f"[db] {result} hadith_id={hadith_id} lang={lang}")
            except Exception as e:
                conn.rollback()
                print(f"[error] DB write failed for hadith {hadith_id} lang={lang}: {e}")
                skipped += 1

            processed += 1
            time.sleep(args.sleep)
            # end row loop
        # end lang loop
    cursor.close()
    conn.close()

    print(f"Done. processed={processed} inserted={inserted} updated={updated} skipped={skipped}")


if __name__ == '__main__':
    main()
