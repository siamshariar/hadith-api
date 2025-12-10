#!/usr/bin/env python3
"""
Validate category imports: compare CSV categories with `categories` and `category_translations` DB tables.
If --fix is passed, update DB rows to match CSV and CSV localizations.

Usage:
  python scripts/validate_and_fix_categories.py --dry-run
  python scripts/validate_and_fix_categories.py --fix
"""

import csv
import os
import argparse
from utils import get_db_connection
from config import CSV_OUTPUT_DIR


def read_csv(path):
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [r for r in reader]


def validate(fix=False):
    cfile = os.path.join(CSV_OUTPUT_DIR, 'categories.csv')
    clfile = os.path.join(CSV_OUTPUT_DIR, 'category_localizations.csv')

    if not os.path.exists(cfile):
        print('Missing categories.csv — generate CSV using step1_generate_complete_chapters.py')
        return
    if not os.path.exists(clfile):
        print('Missing category_localizations.csv — generate CSV using step1_generate_complete_chapters.py')
        return

    categories = read_csv(cfile)
    clocal = read_csv(clfile)

    conn = get_db_connection()
    cursor = conn.cursor()

    mismatches = []
    updates = 0

    for cat in categories:
        cid = int(cat.get('id'))
        # find DB category
        cursor.execute('SELECT title, parent_id FROM categories WHERE id = %s', (cid,))
        row = cursor.fetchone()
        if not row:
            print(f'[MISSING] Category {cid} not found in DB. CSV title: {cat.get("name_en")}')
            continue
        db_title, db_parent = row
        csv_title = cat.get('name_en')
        # Compare
        if (db_title or '').strip() != (csv_title or '').strip():
            mismatches.append((cid, db_title, csv_title))
            if fix:
                cursor.execute('UPDATE categories SET title=%s, updated_at=NOW() WHERE id=%s', (csv_title, cid))
                updates += 1

        # check category localizations
        locs = [c for c in clocal if c.get('category_id') == str(cid)]
        for loc in locs:
            code = loc.get('localization_code')
            csv_loc_title = loc.get('name')
            cursor.execute('SELECT title FROM category_translations WHERE category_id=%s AND localization_code=%s', (cid, code))
            row2 = cursor.fetchone()
            db_loc_title = row2[0] if row2 else None
            if (db_loc_title or '').strip() != (csv_loc_title or '').strip():
                mismatches.append((cid, f'{code}:{db_loc_title}', f'{code}:{csv_loc_title}'))
                if fix:
                    if row2:
                        cursor.execute('UPDATE category_translations SET title=%s, updated_at=NOW() WHERE category_id=%s AND localization_code=%s', (csv_loc_title, cid, code))
                    else:
                        cursor.execute('INSERT INTO category_translations (category_id, localization_code, title, created_at, updated_at) VALUES (%s,%s,%s,NOW(),NOW())', (cid, code, csv_loc_title))
                    updates += 1

    if fix and updates:
        conn.commit()
    print('\n=== Validation complete ===')
    print(f'Mismatches found: {len(mismatches)}')
    if fix:
        print(f'Updates applied: {updates}')
    if mismatches:
        for m in mismatches[:50]:
            print('Mismatch:', m)

    cursor.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fix', action='store_true', help='Apply fixes to DB to match CSV')
    parser.add_argument('--dry-run', action='store_true', help='Check matches without applying fixes')
    args = parser.parse_args()
    validate(fix=args.fix and not args.dry_run)


if __name__ == '__main__':
    main()
