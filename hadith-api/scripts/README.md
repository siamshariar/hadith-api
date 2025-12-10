# Import / Sync scripts

This folder contains helper scripts to detect and import missing translations for Hadith data.

Main scripts:
- `sync_missing_translations.py` - Sync missing translations using prioritized sources. Includes support for fawaz, hadeethenc and alquranbd (Bengali) sources.
- `import_all_missing_translations.py` - Orchestrator to run sync across multiple languages (dry-run before doing actual import).
- `import_translations_from_file.php` - Import translations from a locally generated JSON export into DB.

Common usage examples:

Dry-run for Bengali (no DB write):
```powershell
python scripts/sync_missing_translations.py --lang bn --books bukhari --limit 200 --dry-run --source alquranbd,fawaz,hadeethenc
```
Note: `--languages` is an alias for `--lang`, (both accept comma separated list of language codes).

Run import for Bengali:
```powershell
python scripts/sync_missing_translations.py --lang bn --books bukhari --limit 500 --source alquranbd,fawaz,hadeethenc

Force / overwrite option (DANGEROUS):
```powershell
# Overwrite existing translations with values fetched from sources. Requires explicit confirmation flag to avoid accidental destructive updates.
python scripts/sync_missing_translations.py --languages bn --overwrite --confirm
```
```

Orchestrate across languages (dry-run then run):
```powershell
python scripts/import_all_missing_translations.py --lang bn,ur --sample 50
python scripts/import_all_missing_translations.py --run --lang bn,ur --sample 50

Full CSV -> DB -> API sync orchestrator (recommended)
```powershell
# This will generate CSVs if missing, import metadata, import categories from HadeethEnc if needed,
# then import hadiths/translations from Fawaz and finally run the missing-translations backfill.
python scripts/full_import_orchestrator.py --yes

# To allow destructive overwrite of existing translations during the final sync add flags:
python scripts/full_import_orchestrator.py --yes --overwrite --confirm
```

# Local import-file example (prioritize local JSON) - useful for manual corrections
python scripts/sync_missing_translations.py --lang bn --books bukhari --import-file=test_bengali_output.json --sample 200 --dry-run

```

If you prefer to trigger from within Laravel (admin-only), there is an Artisan command and an admin route:
- Artisan: `php artisan sync:missing-translations --lang=bn --books=bukhari --limit=200` (adds `--dry-run` to not write DB)
- HTTP: `POST /api/admin/sync-missing-translations` with JSON body `{ "lang":"bn","books":"bukhari","limit":200,"dry_run":true }` (secure the route with middleware)
 - Artisan: `php artisan sync:missing-translations --lang=bn --books=bukhari --limit=200` (adds `--dry-run` to not write DB)
 - HTTP: `POST /api/admin/sync-missing-translations` with JSON body `{ "lang":"bn","books":"bukhari","limit":200,"dry_run":true }` (secure the route with middleware)

After run checks:

```
# Report missing translations (before & after)
php scripts/report_missing_translations.php --lang bn --output=missing_bn.json

# Check translation counts per language
php scripts/check_translation_summary.php --lang bn

# Quick verification script
```powershell
python scripts/verify_full_import.py
```

# Validate categories before/after import
```powershell
python scripts/validate_and_fix_categories.py --dry-run
# to actually correct DB entries to match CSV:
python scripts/validate_and_fix_categories.py --fix
```

```

Notes:
- The scripts expect `requests` and `mysql-connector-python` that are in `scripts/requirements.txt`. To install packages use:
```
python -m pip install -r scripts/requirements.txt
```
- Add `alquranbd` to `--source` when trying to import Bengali translations; it fetches chapter-level hadiths and attempts to match hadith numbers.
- If a remote source returns empty translation text the importer will skip those and report them in `sync_reports`.

Safety & overwrite:
- The `--overwrite` flag will ask the script to update existing translations — this can be destructive. To avoid accidental data loss the CLI requires `--confirm` as a second flag when `--overwrite` is used.
- When using the Laravel `sync:missing-translations` command, pass `--overwrite` and `--confirm` to enable mass overwrite in a controlled environment. Prefer running a `--dry-run` first and backing up DB.

Security:
- Protect the admin endpoint with auth middleware or only run `php artisan sync:missing-translations` from a trusted cron or background job.

Queue usage:

```
php artisan sync:missing-translations --lang=bn --books=bukhari --queue
php artisan queue:work --tries=3
```
	Example (routes/api.php):

```php
// Protect admin sync under auth and admin middleware
Route::post('/admin/sync-missing-translations', [HadithController::class, 'syncMissingTranslations'])
		->middleware(['auth:api','role:admin']);
```
Replace `auth:api` and `role:admin` with your project's preferred middleware stack.

If you want, I can add a queue worker or secure middleware for the admin route next.