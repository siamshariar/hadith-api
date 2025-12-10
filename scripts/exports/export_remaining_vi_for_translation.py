#!/usr/bin/env python3
"""
Export remaining Vietnamese hadith IDs with English text and context for translation work.
Writes `scripts/exports/remaining_vi_for_translation.csv` with columns:
  hadith_id, book_id, chapter_id, book_name_en, chapter_name_en, hadith_number, en_translation, arabic_text

Usage:
  python scripts/exports/export_remaining_vi_for_translation.py
"""
import os
import csv
import sys

# Project root (hadith-api)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPORT_DIR = os.path.join(PROJECT_ROOT, 'scripts', 'exports')
MISSING_DIR = os.path.join(PROJECT_ROOT, 'scripts', 'missing_translations')
OUT_PATH = os.path.join(EXPORT_DIR, 'remaining_vi_for_translation.csv')

# load DB config
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts'))
try:
    import config
except Exception as e:
    print('ERROR: could not import scripts/config.py:', e)
    sys.exit(2)

try:
    import mysql.connector
except Exception as e:
    print('ERROR: mysql-connector-python not available:', e)
    sys.exit(2)


def get_db_connection():
    return mysql.connector.connect(**config.DB_CONFIG)


def load_missing_ids():
    path = os.path.join(MISSING_DIR, 'missing_vi.csv')
    if not os.path.isfile(path):
        print('ERROR: missing file', path)
        return []
    ids = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ids.append(int(row['hadith_id']))
            except Exception:
                continue
    return ids


def fetch_context(cursor, hid):
    # default values
    book_id = None
    chapter_id = None
    hadith_number = None
    arabic_text = ''
    en_text = ''
    book_name = ''
    chapter_name = ''

    cursor.execute('SELECT id, book_id, chapter_id, hadith_number, arabic_text FROM hadiths WHERE id=%s', (hid,))
    row = cursor.fetchone()
    if row:
        # id returned first column too; map by position
        _, book_id, chapter_id, hadith_number, arabic_text = row
    # english translation if exists
    cursor.execute('SELECT translation_text FROM hadith_translations WHERE hadith_id=%s AND localization_code=%s LIMIT 1', (hid, 'en'))
    r = cursor.fetchone()
    if r:
        en_text = r[0]
    # book name
    if book_id:
        cursor.execute('SELECT name_en FROM books WHERE id=%s LIMIT 1', (book_id,))
        r = cursor.fetchone()
        if r:
            book_name = r[0]
    # chapter name
    if chapter_id:
        cursor.execute('SELECT name_en FROM chapters WHERE id=%s LIMIT 1', (chapter_id,))
        r = cursor.fetchone()
        if r:
            chapter_name = r[0]

    return {
        'hadith_id': hid,
        'book_id': book_id,
        'chapter_id': chapter_id,
        'book_name_en': book_name or '',
        'chapter_name_en': chapter_name or '',
        'hadith_number': hadith_number or '',
        'en_translation': en_text or '',
        'arabic_text': arabic_text or ''
    }


def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    ids = load_missing_ids()
    if not ids:
        print('No missing IDs found; did you run `export_missing_translations.py` first?')
        return

    conn = get_db_connection()
    cur = conn.cursor()

    with open(OUT_PATH, 'w', newline='', encoding='utf-8') as out:
        writer = csv.writer(out)
        writer.writerow(['hadith_id','book_id','chapter_id','book_name_en','chapter_name_en','hadith_number','en_translation','arabic_text'])
        count = 0
        for hid in ids:
            ctx = fetch_context(cur, hid)
            writer.writerow([
                ctx['hadith_id'], ctx['book_id'], ctx['chapter_id'], ctx['book_name_en'], ctx['chapter_name_en'], ctx['hadith_number'], ctx['en_translation'], ctx['arabic_text']
            ])
            count += 1

    cur.close()
    conn.close()
    print(f'Wrote {count} rows -> {OUT_PATH}')


if __name__ == '__main__':
    main()
