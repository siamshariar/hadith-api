#!/usr/bin/env python3
"""
Orchestrator script: import missing translations for all configured languages.

Usage:
  # Dry-run across all languages
  python scripts/import_all_missing_translations.py --dry-run

  # Run import for all languages (be careful; this may hit remote sources and take a long time)
  python scripts/import_all_missing_translations.py --run

  # Run import only for specific languages
  python scripts/import_all_missing_translations.py --run --languages bn,ur

Options:
  --sample N: limit items per language for testing
  --import-file path: optional JSON with translations to add before fetching

This script uses `scripts/sync_missing_translations.py` internally.
"""
import subprocess
import argparse
import json
import os
from config import LOCALIZATION_MAP


def parse_args():
    p = argparse.ArgumentParser(description='Orchestrate imports for all languages')
    p.add_argument('--run', action='store_true', help='Run actual import (not dry-run)')
    p.add_argument('--lang', type=str, default=None, help='Comma-separated languages to process (defaults to all)')
    p.add_argument('--sample', type=int, default=None, help='Pass through to sync script to limit processed items')
    p.add_argument('--import-file', type=str, default=None, help='Pass a JSON file to sync script that gets prioritized')
    p.add_argument('--verbose', action='store_true')
    return p.parse_args()


def list_languages(filter_list=None):
    keys = list(LOCALIZATION_MAP.keys())
    if filter_list:
        want = [l.strip() for l in filter_list.split(',') if l.strip()]
        keys = [k for k in keys if k in want]
    return keys


def run_sync_for_lang(lang, dry_run=True, sample=None, import_file=None, verbose=False):
    cmd = ["python", "scripts/sync_missing_translations.py", "--lang", lang]
    if dry_run:
        cmd.append("--dry-run")
    if sample:
        cmd.extend(["--sample", str(sample)])
    if import_file:
        cmd.extend(["--import-file", import_file])
    if verbose:
        cmd.append("--verbose")
    print('Running:', ' '.join(cmd))
    proc = subprocess.run(cmd, capture_output=False)
    return proc.returncode


def main():
    args = parse_args()
    langs = list_languages(args.lang)
    print(f"Languages to process: {langs}")

    # First, dry-run all languages unless --run
    for lang in langs:
        print(f"\n--- DRY-RUN for {lang} ---")
        run_sync_for_lang(lang, dry_run=True, sample=args.sample, import_file=args.import_file, verbose=args.verbose)

    if args.run:
        print('\nStarting actual import runs...')
        for lang in langs:
            print(f"\n--- IMPORT for {lang} ---")
            # Call sync script without dry-run
            return_code = run_sync_for_lang(lang, dry_run=False, sample=args.sample, import_file=args.import_file, verbose=args.verbose)
            if return_code != 0:
                print(f"Warning: sync script returned {return_code} for language {lang}")

    print('\nAll done.')


if __name__ == '__main__':
    main()
