#!/usr/bin/env python3
r"""Run a comprehensive import sequence using existing orchestrator scripts.

This wrapper runs the CSV import, then Fawaz, HadeethEnc, and Bangla imports
separately (idempotent). It can export missing translation IDs per language
and optionally run the targeted HadeethEnc checker for missing IDs.

Usage:
    python .\scripts\run_full_import_manager.py --yes --run-targeted vi,si
"""
import os
import sys
import csv
import time
import argparse
import subprocess
from typing import List

try:
    from config import DB_CONFIG, LOCALIZATION_MAP
except Exception:
    # When executed from repository root as `python .\scripts\...`, config imports work.
    # If not, adjust sys.path to include scripts directory.
    sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
    from config import DB_CONFIG, LOCALIZATION_MAP

import mysql.connector


LOG_DIR = os.path.join('scripts', 'import_runs')
os.makedirs(LOG_DIR, exist_ok=True)


def run_cmd(cmd: List[str], log_file: str = None, check: bool = True):
    print(f"Running: {' '.join(cmd)}")
    env = os.environ.copy()
    # Force Python subprocesses to use UTF-8 output on Windows to avoid
    # UnicodeEncodeError when the child prints emoji or non-encodable chars.
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'

    # Ensure the parent decodes child stdout as UTF-8 to avoid
    # UnicodeDecodeError when Windows default encoding can't decode bytes.
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', env=env) as p:
        out_lines = []
        for line in p.stdout:
            print(line.rstrip())
            out_lines.append(line)
    if log_file:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.writelines(out_lines)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)} (code={p.returncode})")


def run_orchestrator_step(step: str, extra_args: List[str] = None):
    """Run one of: csv, fawaz, hadeethenc, bangla or full"""
    extra_args = extra_args or []
    base = ['python', os.path.join('scripts', 'master_import_orchestrator.py'), '--yes']
    if step == 'csv':
        cmd = base + ['--skip-hadeethenc', '--skip-fawaz', '--skip-bangla'] + extra_args
    elif step == 'fawaz':
        cmd = base + ['--skip-csv', '--skip-hadeethenc', '--skip-bangla'] + extra_args
    elif step == 'hadeethenc':
        cmd = base + ['--skip-csv', '--skip-fawaz', '--skip-bangla'] + extra_args
    elif step == 'bangla':
        cmd = base + ['--skip-csv', '--skip-hadeethenc', '--skip-fawaz'] + extra_args
    elif step == 'full':
        cmd = base + extra_args
    else:
        raise ValueError('unknown step')

    logfile = os.path.join(LOG_DIR, f'{int(time.time())}_{step}.log')
    run_cmd(cmd, log_file=logfile)
    return logfile


def export_missing_ids(lang: str, out_csv: str):
    """Export hadith IDs missing translation for `lang` to CSV with context."""
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)
    sql = (
        "SELECT h.id AS hadith_id, h.book_id, h.chapter_id, h.hadith_number, h.arabic_text "
        "FROM hadiths h LEFT JOIN hadith_translations t "
        "ON h.id = t.hadith_id AND t.localization_code = %s "
        "WHERE t.id IS NULL"
    )
    cur.execute(sql, (lang,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['hadith_id', 'book_id', 'chapter_id', 'hadith_number', 'arabic_text'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {len(rows)} missing rows -> {out_csv}")
    return len(rows)


def run_targeted_checker(lang: str):
    """Run the targeted HadeethEnc checker for a language (if present)."""
    checker = os.path.join('scripts', 'targeted_hadeethenc_checker.py')
    if not os.path.exists(checker):
        print("targeted_hadeethenc_checker.py not found, skipping targeted check")
        return None
    cmd = ['python', checker, '--lang', lang]
    logfile = os.path.join(LOG_DIR, f'{int(time.time())}_targeted_{lang}.log')
    run_cmd(cmd, log_file=logfile)
    return logfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--yes', action='store_true')
    parser.add_argument('--run-targeted', help='Comma-separated language codes to run targeted checker after main imports')
    parser.add_argument('--export-missing', help='Comma-separated language codes to export missing IDs', default='')
    parser.add_argument('--steps', help='Comma-separated steps: csv,fawaz,hadeethenc,bangla,full', default='full')
    args = parser.parse_args()

    steps = [s.strip() for s in args.steps.split(',') if s.strip()]

    try:
        if 'csv' in steps or 'full' in steps:
            print('\n== STEP: CSV import ==')
            run_orchestrator_step('csv')

        if 'fawaz' in steps or 'full' in steps:
            print('\n== STEP: Fawaz import ==')
            run_orchestrator_step('fawaz')

        if 'hadeethenc' in steps or 'full' in steps:
            print('\n== STEP: HadeethEnc import ==')
            run_orchestrator_step('hadeethenc')

        if 'bangla' in steps or 'full' in steps:
            print('\n== STEP: Bangla import ==')
            run_orchestrator_step('bangla')

        # Run fix and verify by invoking the orchestrator with all import steps skipped
        # (this calls fix_missing_data() and verify_import() inside the script)
        print('\n== STEP: Fixing and verification ==')
        run_orchestrator_step('full', extra_args=['--skip-csv', '--skip-hadeethenc', '--skip-fawaz', '--skip-bangla'])

        # Export missing IDs if requested
        if args.export_missing:
            langs = [l.strip() for l in args.export_missing.split(',') if l.strip()]
            for lang in langs:
                out = os.path.join('scripts', 'missing_translations', f'missing_{lang}.csv')
                export_missing_ids(lang, out)

        # Run targeted checker for selected languages
        if args.run_targeted:
            langs = [l.strip() for l in args.run_targeted.split(',') if l.strip()]
            for lang in langs:
                # Ensure missing CSV exists; if not, export it first
                missing_csv = os.path.join('scripts', 'missing_translations', f'missing_{lang}.csv')
                if not os.path.exists(missing_csv):
                    export_missing_ids(lang, missing_csv)
                run_targeted_checker(lang)

        print('\nAll requested steps completed successfully')

    except Exception as e:
        print(f'ERROR: {e}')
        raise


if __name__ == '__main__':
    main()
