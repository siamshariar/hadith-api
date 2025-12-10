#!/usr/bin/env python3
"""
Idempotent importer for categories, subcategories and hadith translations.

Usage:
  - Dry run (no DB writes):
      python scripts/import_categories_and_translations.py --dry-run

  - Apply changes (will connect to DB using `scripts/config.py`):
      python scripts/import_categories_and_translations.py --apply

Behavior:
  - Imports `csv-categories/categories.csv` into `categories` table (id, parent_id, slug)
  - Imports `csv-categories/category_localizations.csv` into `category_localizations` (category_id, localization_code, name, slug)
  - Optionally applies translation JSONL files from `scripts/targeted_results/found_{lang}.jsonl` into `hadith_translations` table.
  - All operations are idempotent: existing rows are updated, missing rows are inserted.
"""
import argparse
import csv
import json
import os
import sys
from typing import Optional

try:
    import mysql.connector
except Exception:
    mysql = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_CAT_DIR = os.path.join(BASE_DIR, 'csv-categories')
TARGETED_DIR = os.path.join(BASE_DIR, 'scripts', 'targeted_results')
CONFIG_PATH = os.path.join(BASE_DIR, 'scripts', 'config.py')

def load_db_config():
    # import local config file
    sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
    try:
        import config as cfg
        return cfg.DB_CONFIG
    except Exception as e:
        print('ERROR: could not import scripts/config.py:', e)
        return None


def connect(db_config):
    if mysql is None:
        raise RuntimeError('mysql-connector-python not available in this environment')
    return mysql.connector.connect(**db_config)


def upsert_category(cursor, cat_id: int, parent_id: Optional[int], slug: str, name_en: str = '', name_ar: str = ''):
    # idempotent insert/update by id
    cursor.execute('SELECT id FROM categories WHERE id = %s', (cat_id,))
    if cursor.fetchone():
        cursor.execute(
            'UPDATE categories SET parent_id=%s, slug=%s, name_en=%s, name_ar=%s WHERE id=%s',
            (parent_id, slug, name_en, name_ar, cat_id)
        )
    else:
        cursor.execute(
            'INSERT INTO categories (id, parent_id, slug, name_en, name_ar) VALUES (%s, %s, %s, %s, %s)',
            (cat_id, parent_id, slug, name_en, name_ar)
        )


def upsert_category_localization(cursor, loc_id: int, category_id: int, localization_code: str, name: str, slug: str):
    # Robust upsert that avoids duplicate-key errors on (category_id, localization_code)
    # Strategy:
    # 1. If a row exists for the (category_id, localization_code) unique key, update it.
    # 2. Else if loc_id provided and an existing row has that id, update that row.
    # 3. Else insert a new row. If loc_id is provided and not used elsewhere, insert with explicit id.

    # 1) check by unique key (category_id + localization_code)
    cursor.execute(
        'SELECT id FROM category_localizations WHERE category_id=%s AND localization_code=%s',
        (category_id, localization_code)
    )
    existing = cursor.fetchone()
    if existing:
        existing_id = existing[0]
        cursor.execute(
            'UPDATE category_localizations SET name=%s, slug=%s WHERE id=%s',
            (name, slug, existing_id)
        )
        return

    # 2) if no unique-key match, but loc_id supplied, check if that id exists
    if loc_id:
        cursor.execute('SELECT id FROM category_localizations WHERE id=%s', (loc_id,))
        if cursor.fetchone():
            cursor.execute(
                'UPDATE category_localizations SET category_id=%s, localization_code=%s, name=%s, slug=%s WHERE id=%s',
                (category_id, localization_code, name, slug, loc_id)
            )
            return
        else:
            # Safe to insert with explicit id (no id conflict and we already checked unique key)
            cursor.execute(
                'INSERT INTO category_localizations (id, category_id, localization_code, name, slug) VALUES (%s, %s, %s, %s, %s)',
                (loc_id, category_id, localization_code, name, slug)
            )
            return

    # 3) no loc_id provided and no unique-key match -> insert normally
    cursor.execute(
        'INSERT INTO category_localizations (category_id, localization_code, name, slug) VALUES (%s, %s, %s, %s)',
        (category_id, localization_code, name, slug)
    )


def apply_found_translations(cursor, jsonl_path: str, lang_code: str):
    """
    Reads JSONL file with lines: {"id": hadith_id, "result": <hadeethenc response>}
    Attempts to extract a translation string and insert into hadith_translations.
    The function is conservative: it will skip entries where it cannot find a usable text.
    """
    inserted = 0
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            hadith_id = obj.get('id') or obj.get('hadith_id')
            result = obj.get('result')
            if not hadith_id or not result:
                continue

            # Attempt common paths for translation text
            text = None
            # 1) direct 'translation' or 'text'
            if isinstance(result, dict):
                for key in ('translation', 'text', 'translation_text'):
                    if key in result and isinstance(result[key], str) and result[key].strip():
                        text = result[key].strip(); break

                # 2) some HadeethEnc responses include 'translations' dict
                if text is None and 'translations' in result and isinstance(result['translations'], dict):
                    cand = result['translations'].get(lang_code) or result['translations'].get('translation')
                    if isinstance(cand, str) and cand.strip():
                        text = cand.strip()

                # 3) 'hadith' -> look for 'text' under nested objects
                if text is None and 'hadith' in result and isinstance(result['hadith'], dict):
                    for key in ('translation', 'text'):
                        if key in result['hadith'] and isinstance(result['hadith'][key], str):
                            text = result['hadith'][key].strip(); break

            if not text:
                # Could not find translation text
                continue

            # idempotent insert into hadith_translations
            cursor.execute('SELECT id FROM hadith_translations WHERE hadith_id=%s AND localization_code=%s', (hadith_id, lang_code))
            if cursor.fetchone():
                cursor.execute('UPDATE hadith_translations SET translation_text=%s WHERE hadith_id=%s AND localization_code=%s',
                               (text, hadith_id, lang_code))
            else:
                # localization_id can be NULL; let DB default or try to map via config import later
                cursor.execute('INSERT INTO hadith_translations (hadith_id, localization_code, translation_text) VALUES (%s, %s, %s)',
                               (hadith_id, lang_code, text))
            inserted += 1
    return inserted


def main():
    p = argparse.ArgumentParser(description='Import categories & apply found hadith translations (idempotent).')
    p.add_argument('--apply', action='store_true', help='Apply changes to DB (default is dry-run)')
    p.add_argument('--apply-translations', action='store_true', help='Also import translations from targeted_results JSONL files')
    args = p.parse_args()

    dry_run = not args.apply

    # Load CSVs
    categories_csv = os.path.join(CSV_CAT_DIR, 'categories.csv')
    catloc_csv = os.path.join(CSV_CAT_DIR, 'category_localizations.csv')
    if not os.path.isfile(categories_csv) or not os.path.isfile(catloc_csv):
        print('ERROR: required CSV files not found in', CSV_CAT_DIR)
        sys.exit(2)

    db_conf = load_db_config()
    if not db_conf and not dry_run:
        print('ERROR: cannot load DB config and not in dry-run mode')
        sys.exit(2)

    conn = None
    cur = None
    if not dry_run:
        conn = connect(db_conf)
        cur = conn.cursor()

    # Process categories
    print('Processing categories from', categories_csv)
    with open(categories_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = int(row['id']) if row.get('id') else None
            parent = int(row['parent_id']) if row.get('parent_id') else None
            slug = row.get('slug') or ''
            name_en = row.get('name_en') or ''
            name_ar = row.get('name_ar') or ''
            if dry_run:
                print(f'[DRY] upsert categories id={cid} parent={parent} slug={slug} name_en="{name_en[:40]}"')
            else:
                upsert_category(cur, cid, parent, slug, name_en, name_ar)

    # Process category localizations
    print('Processing category localizations from', catloc_csv)
    with open(catloc_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            loc_id = int(row['id']) if row.get('id') else None
            cat_id = int(row['category_id']) if row.get('category_id') else None
            code = row.get('localization_code') or 'en'
            name = row.get('name') or ''
            slug = row.get('slug') or ''
            if dry_run:
                print(f'[DRY] upsert category_localization id={loc_id} cat={cat_id} code={code} name="{name[:40]}"')
            else:
                upsert_category_localization(cur, loc_id, cat_id, code, name, slug)

    # Optionally apply translations
    total_inserted = 0
    if args.apply_translations:
        print('Applying translations from', TARGETED_DIR)
        for fname in os.listdir(TARGETED_DIR):
            if not fname.startswith('found_') or not fname.endswith('.jsonl'):
                continue
            lang = fname[len('found_'):-len('.jsonl')]
            path = os.path.join(TARGETED_DIR, fname)
            print(' ->', path)
            if dry_run:
                print(f'[DRY] would apply translations for {lang} from {path}')
                continue
            inserted = apply_found_translations(cur, path, lang)
            total_inserted += inserted
            print(f'   inserted/updated {inserted} translations for {lang}')

    if not dry_run:
        conn.commit()
        cur.close()
        conn.close()

    print('Done. Dry-run=' + str(dry_run) + (f', translations applied={total_inserted}' if args.apply_translations and not dry_run else ''))


if __name__ == '__main__':
    main()
