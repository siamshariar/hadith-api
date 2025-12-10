#!/usr/bin/env python3
"""
Import hadith translations from a CSV file.
CSV format (headers): hadith_id,localization_code,translation_text
Example:
  hadith_id,localization_code,translation_text
  1690,bn,"Translation text here"

This script upserts rows into `hadith_translations` and will set `localization_id` using `LOCALIZATION_MAP` if available.
"""
import csv
import argparse
from utils import get_db_connection
from config import LOCALIZATION_MAP


def parse_args():
    p = argparse.ArgumentParser(description='Import translations from CSV')
    p.add_argument('--file', required=True, help='CSV file path')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--verbose', action='store_true')
    return p.parse_args()


def upsert(cursor, hadith_id, lang, text):
    localization_id = LOCALIZATION_MAP.get(lang, {}).get('id') if lang in LOCALIZATION_MAP else None
    cursor.execute("SELECT id FROM hadith_translations WHERE hadith_id = %s AND localization_code = %s", (hadith_id, lang))
    row = cursor.fetchone()
    now = __import__('time').strftime('%Y-%m-%d %H:%M:%S')
    if row:
        tid = row[0]
        cursor.execute("UPDATE hadith_translations SET translation_text = %s, updated_at = %s WHERE id = %s", (text, now, tid))
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
    conn = get_db_connection()
    cursor = conn.cursor()
    processed = 0
    inserted = 0
    updated = 0

    with open(args.file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                hadith_id = int(row.get('hadith_id') or row.get('id'))
                lang = (row.get('localization_code') or row.get('lang') or row.get('language') or '').strip()
                text = row.get('translation_text') or row.get('text') or ''
                if not hadith_id or not lang or not text:
                    if args.verbose:
                        print(f"Skipping invalid row: {row}")
                    continue

                if args.dry_run:
                    print(f"DRY: would upsert hadith_id={hadith_id} lang={lang}")
                    processed += 1
                    continue

                res = upsert(cursor, hadith_id, lang, text)
                if res == 'inserted':
                    inserted += 1
                else:
                    updated += 1
                processed += 1
            except Exception as e:
                print(f"Error processing row {row}: {e}")
                continue

    if not args.dry_run:
        conn.commit()
    cursor.close()
    conn.close()
    print(f"Done. processed={processed} inserted={inserted} updated={updated}")


if __name__ == '__main__':
    main()
