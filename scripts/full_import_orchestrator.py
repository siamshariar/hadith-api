#!/usr/bin/env python3
"""
Orchestrator: Run CSV -> DB -> API fallback pipeline to ensure complete hadith/catalog data

Steps
- Generate CSV files (books, chapters, categories) with `step1_generate_complete_chapters.py` if missing
- Import CSV into DB with `step2_import_metadata_from_csv.py`
- If categories missing translations, import from `HadeethEnc` categories using import script
- Run Fawaz importer for hadiths & translations (Arabic then other languages)
- Run the `sync_missing_translations.py` script to backfill any missing translations

This script is idempotent and checks the database to avoid re-importing existing data.

Usage: python scripts/full_import_orchestrator.py [--yes] [--overwrite]
"""

import os
import subprocess
import argparse
import mysql.connector
from config import DB_CONFIG, LOCALIZATION_MAP


def run_cmd(cmd, cwd=None, check=False, input_text=None):
    print(f"Running: {cmd}")
    proc = subprocess.Popen(cmd, shell=True, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate(input_text)
    print(out)
    if err:
        print("ERR: ", err)
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return out, err


def get_db_conn():
    return mysql.connector.connect(**DB_CONFIG)


def csv_generate_if_missing():
    # if chapters.csv missing, run step1
    if not os.path.exists(os.path.join('csv_exports', 'chapters.csv')):
        print("chapters.csv missing — generating CSVs using step1_generate_complete_chapters.py")
        run_cmd('python scripts/step1_generate_complete_chapters.py', check=True)
    else:
        print('CSV files already present — skipping generation')


def import_csv_to_db():
    print('\nImporting CSV metadata into DB...')
    run_cmd('python scripts/step2_import_metadata_from_csv.py', check=True)


def check_categories_and_import_hadeethenc():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM categories')
    count = cur.fetchone()[0]
    cur.close()
    conn.close()

    if count == 0:
        print('No categories found in DB — importing from HadeethEnc (categories only)')
        # call import_categories function directly
        cmd = 'python -c "from import_hadeethenc_complete_100_percent import import_categories; import_categories()"'
        run_cmd(cmd, check=True)
    else:
        print(f'Categories table already has {count} entries — skipping HadeethEnc categories import')


def run_fawaz_import(prefer_hadeethenc=True):
    # Build languages list from config
    languages = ','.join(list(LOCALIZATION_MAP.keys()))
    print('Running Fawaz hadith importer for languages:', languages)
    cmd = f"python scripts/step4_import_hadiths_fawaz.py --languages {languages}"
    if prefer_hadeethenc:
        cmd += ' --prefer-hadeethenc'
    run_cmd(cmd, check=True)


def run_sync_missing(overwrite=False, confirm=False):
    # Run backfill script - will do dry-run by default
    languages = ','.join(list(LOCALIZATION_MAP.keys()))
    cmd = f"python scripts/sync_missing_translations.py --languages {languages}"
    if overwrite:
        cmd += ' --overwrite'
        if confirm:
            cmd += ' --confirm'
        else:
            print('WARNING: --overwrite requested but --confirm not set — aborting')
            return

    run_cmd(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description='Full import: CSV -> DB -> API fallback to ensure complete data')
    parser.add_argument('--yes', action='store_true', help='Answer yes to all confirmations')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing translations during sync step (dangerous)')
    parser.add_argument('--confirm', action='store_true', help='Required with --overwrite to allow destructive updates')
    args = parser.parse_args()

    csv_generate_if_missing()
    import_csv_to_db()
    check_categories_and_import_hadeethenc()

    print('\nNow importing hadith texts and translations from Fawaz API (this may take hours)')
    if not args.yes:
        r = input('Proceed with Fawaz import? (yes/no): ')
        if r.lower() != 'yes':
            print('Import aborted by user')
            return
    run_fawaz_import(prefer_hadeethenc=True)

    print('\nRunning sync to backfill any missing translations using our sources')
    # Query languages for missing counts
    conn = get_db_conn()
    cur = conn.cursor()
    languages = list(LOCALIZATION_MAP.keys())
    missing_langs = []
    for lang in languages:
        cur.execute("SELECT COUNT(1) FROM hadiths h LEFT JOIN hadith_translations t ON h.id=t.hadith_id AND t.localization_code=%s WHERE t.id IS NULL", (lang,))
        count = cur.fetchone()[0]
        print(f"Language {lang}: missing {count} translations")
        if count > 0:
            missing_langs.append(lang)
    cur.close()
    conn.close()

    if not missing_langs:
        print('No missing translations detected — sync step skipped')
    else:
        langs_csv = ','.join(missing_langs)
        print('Will sync missing translations for: ', langs_csv)
        run_cmd(f'python scripts/sync_missing_translations.py --languages {langs_csv} {"--overwrite --confirm" if args.overwrite and args.confirm else ""}', check=True)


if __name__ == '__main__':
    main()
