#!/usr/bin/env python3
r"""Full, one-shot import pipeline wrapper.

Steps performed:
 - Convert `scripts/csv_exports/categories_multilingual.csv` -> `csv-categories/categories.csv` and `csv-categories/category_localizations.csv`
 - Invoke `scripts/run_full_import_manager.py` to run CSV import and API imports (HadeethEnc, Fawaz, Bangla) and verification
 - Optionally export missing translation IDs and run targeted checks
 - Optionally import prepared translation CSVs (dry-run by default)

This script uses the existing orchestrator and import scripts to avoid duplicating DB logic.
"""

import os
import sys
import csv
import argparse
import subprocess
import time


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_EXPORT = os.path.join(BASE, 'scripts', 'csv_exports', 'categories_multilingual.csv')
CSV_CAT_DIR = os.path.join(BASE, 'csv-categories')
MANAGER = os.path.join(BASE, 'scripts', 'run_full_import_manager.py')


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)


def convert_categories_multilingual(src_path: str, out_dir: str) -> (str, str):
    """Convert multilingual categories CSV into two CSVs expected by importers.

    Returns (categories_csv_path, category_localizations_csv_path)
    """
    ensure_dir(out_dir)

    with open(src_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Determine language name columns that start with 'name_'
        name_cols = [h for h in headers if h.startswith('name_')]

        categories_path = os.path.join(out_dir, 'categories.csv')
        catlocs_path = os.path.join(out_dir, 'category_localizations.csv')

        # Write categories.csv: id,parent_id,slug,name_en,name_ar
        with open(categories_path, 'w', newline='', encoding='utf-8') as catf, \
             open(catlocs_path, 'w', newline='', encoding='utf-8') as locf:
            cat_writer = csv.writer(catf)
            loc_fieldnames = ['category_id', 'localization_code', 'name', 'slug']
            loc_writer = csv.writer(locf)

            cat_writer.writerow(['id', 'parent_id', 'slug', 'name_en', 'name_ar'])
            loc_writer.writerow(['id', 'category_id', 'localization_code', 'name', 'slug'])

            next_loc_id = 1
            for row in reader:
                cid = row.get('id') or ''
                parent = row.get('parent_id') or ''
                slug = row.get('slug') or ''
                name_en = row.get('name_en') or ''
                name_ar = row.get('name_ar') or ''

                cat_writer.writerow([cid, parent, slug, name_en, name_ar])

                # write localization rows for every name_* column
                for col in name_cols:
                    # column like name_vi -> lang code vi
                    lang = col.split('name_', 1)[-1]
                    text = row.get(col) or ''
                    if not text:
                        continue
                    # id left empty (let DB assign) but keep a monotonically increasing id to be safe
                    loc_writer.writerow([next_loc_id, cid, lang, text, slug])
                    next_loc_id += 1

    print(f"Converted {src_path} -> {categories_path}, {catlocs_path}")
    return categories_path, catlocs_path


def run_manager(steps: str = 'full', export_missing: str = '', run_targeted: str = '', yes: bool = False):
    cmd = [sys.executable, MANAGER, '--steps', steps]
    if export_missing:
        cmd += ['--export-missing', export_missing]
    if run_targeted:
        cmd += ['--run-targeted', run_targeted]
    if yes:
        cmd += ['--yes']

    env = os.environ.copy()
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'

    logfile = os.path.join('scripts', 'import_runs', f'{int(time.time())}_full_import.log')
    print('Running manager:', ' '.join(cmd))
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', env=env) as p:
        lines = []
        for ln in p.stdout:
            print(ln.rstrip())
            lines.append(ln)
    with open(logfile, 'w', encoding='utf-8') as lf:
        lf.writelines(lines)
    if p.returncode != 0:
        raise RuntimeError(f'Manager failed (code={p.returncode}), see {logfile}')
    print('Manager completed, log ->', logfile)
    return logfile


def import_translations_from_csv(file_path: str, apply: bool = False, dry_run: bool = True):
    """Invoke the existing import_translations_from_csv.py script."""
    script = os.path.join(BASE, 'scripts', 'import_translations_from_csv.py')
    cmd = [sys.executable, script, '--file', file_path]
    if dry_run:
        cmd.append('--dry-run')
    if apply:
        cmd = [sys.executable, script, '--file', file_path, '--verbose']

    env = os.environ.copy()
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'

    print('Running translation importer:', ' '.join(cmd))
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', env=env) as p:
        for ln in p.stdout:
            print(ln.rstrip())
    if p.returncode != 0:
        raise RuntimeError(f'Translation importer failed (code={p.returncode})')


def apply_found_translations_via_categories(apply: bool = False):
    """Apply any found_{lang}.jsonl files using import_categories_and_translations.py

    This uses the existing script which already contains a safe apply_found_translations
    path and is idempotent.
    """
    script = os.path.join(BASE, 'scripts', 'import_categories_and_translations.py')
    if not os.path.exists(script):
        print('import_categories_and_translations.py not found, cannot apply JSONL translations')
        return None

    cmd = [sys.executable, script]
    if apply:
        cmd += ['--apply', '--apply-translations']
    else:
        cmd += ['--apply-translations']

    env = os.environ.copy()
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'

    print('Running:', ' '.join(cmd))
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', env=env) as p:
        for ln in p.stdout:
            print(ln.rstrip())
    if p.returncode != 0:
        raise RuntimeError(f'apply translations command failed (code={p.returncode})')
    return True


def parse_args():
    p = argparse.ArgumentParser(description='Full import pipeline: CSV convert + manager + optional translation import')
    p.add_argument('--csv', default=CSV_EXPORT, help='Path to multilingual categories CSV')
    p.add_argument('--generate-csvs-only', action='store_true', help='Only generate csv-categories files and exit')
    p.add_argument('--steps', default='full', help='Steps to pass to manager (csv,fawaz,hadeethenc,bangla,full)')
    p.add_argument('--export-missing', help='Comma list of langs to export missing IDs')
    p.add_argument('--run-targeted', help='Comma list of langs to run targeted HadeethEnc checker')
    p.add_argument('--import-translations-file', help='Path to prepared translations CSV to import after manager (optional)')
    p.add_argument('--apply-translations', action='store_true', help='Actually apply translations (default dry-run)')
    p.add_argument('--fill-missing', action='store_true', help='Export missing IDs, run targeted HadeethEnc checks for all missing languages, and apply found translations')
    p.add_argument('--use-ultimate', action='store_true', help='Invoke scripts/ultimate_import_solution.py (full all-source importer) instead of manager')
    p.add_argument('--yes', action='store_true', help='Auto-confirm prompts forwarded to manager')
    return p.parse_args()


def main():
    args = parse_args()

    csv_path = args.csv
    if not os.path.exists(csv_path):
        print('ERROR: categories multilingual CSV not found:', csv_path)
        sys.exit(2)

    ensure_dir(CSV_CAT_DIR)
    categories_csv, catloc_csv = convert_categories_multilingual(csv_path, CSV_CAT_DIR)

    if args.generate_csvs_only:
        print('Generated CSVs and exiting (no DB actions)')
        return

    # If requested, run ultimate_import_solution which performs a comprehensive import
    if args.use_ultimate:
        ultimate = os.path.join(BASE, 'scripts', 'ultimate_import_solution.py')
        if not os.path.exists(ultimate):
            print('❌ ultimate_import_solution.py not found, falling back to manager')
        else:
            cmd = [sys.executable, ultimate]
            if args.yes:
                # ultimate script currently has no --yes flag; it is aggressive by default
                pass
            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'
            print('Running ultimate importer:', ' '.join(cmd))
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', env=env) as p:
                lines = []
                for ln in p.stdout:
                    print(ln.rstrip())
                    lines.append(ln)
            ul_log = os.path.join('scripts', 'import_runs', f'{int(time.time())}_ultimate.log')
            with open(ul_log, 'w', encoding='utf-8') as lf:
                lf.writelines(lines)
            if p.returncode != 0:
                raise RuntimeError(f'Ultimate importer failed (code={p.returncode}). See {ul_log}')
            print('Ultimate importer completed, log ->', ul_log)
            logfile = ul_log
            # after ultimate import, optionally export missing and/or run targeted checks
            if args.export_missing:
                pass
            # if user asked to fill missing with targeted checker we'll continue below
    else:
        # Run manager to import CSVs and fetch from APIs
        logfile = run_manager(steps=args.steps, export_missing=args.export_missing or '', run_targeted=args.run_targeted or '', yes=args.yes)

    # Optionally import prepared translations CSV
    if args.import_translations_file:
        file_path = args.import_translations_file
        if not os.path.exists(file_path):
            print('Translations CSV not found:', file_path)
        else:
            import_translations_from_csv(file_path, apply=args.apply_translations, dry_run=not args.apply_translations)

    # Fill missing pipeline: export -> targeted HadeethEnc -> apply found JSONL
    if args.fill_missing:
        print('\n== FILL MISSING: exporting missing IDs for all languages in LOCALIZATION_MAP ==')
        # get all localization codes from config
        from config import LOCALIZATION_MAP as _LM
        langs = list(_LM.keys())
        # export missing IDs via manager per-language
        for lang in langs:
            missing_csv = os.path.join('scripts', 'missing_translations', f'missing_{lang}.csv')
            print(f'Exporting missing IDs for {lang} -> {missing_csv}')
            run_manager(steps='csv', export_missing=lang, yes=args.yes)

        # Run targeted checks for languages to gather found_{lang}.jsonl
        print('\n== Running targeted HadeethEnc checks for all missing languages ==')
        def run_targeted_checker(lang_code: str):
            """Run the targeted_hadeethenc_checker.py for a single language code.

            Runs in a subprocess with PYTHONUTF8 and PYTHONIOENCODING set, prints live output
            and does not raise on non-zero returncode (we want to continue other langs).
            """
            script = os.path.join('scripts', 'targeted_hadeethenc_checker.py')
            cmd = [sys.executable, script, '--lang', lang_code]
            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'

            print('Running targeted checker:', ' '.join(cmd))
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', env=env) as p:
                for ln in p.stdout:
                    print(ln.rstrip())
            if p.returncode != 0:
                # don't raise to allow continuing with remaining languages
                print(f'Warning: targeted checker for {lang_code} exited with code {p.returncode}')

        for lang in langs:
            print('->', lang)
            run_targeted_checker(lang)

        # Apply found JSONL files using import_categories_and_translations
        print('\n== Applying found translations into DB (dry-run unless --apply-translations was set) ==')
        apply_found_translations_via_categories(apply=args.apply_translations)

    print('Full import pipeline completed. See manager log:', logfile)


if __name__ == '__main__':
    main()
