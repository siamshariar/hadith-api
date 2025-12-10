# Orchestrator runner for Windows PowerShell
# Usage: .\scripts\run_full_import.ps1

# 1. Generate CSVs and import metadata (books, categories, chapters)
python .\scripts\step1_generate_complete_chapters.py
python .\scripts\step2_import_metadata_from_csv.py

# 2. Import categories and hadiths from HadeethEnc if needed
# This will not prompt if you run the orchestrator with --yes
python .\scripts\full_import_orchestrator.py --yes

# 3. After run: check missing translations
php scripts/check_translation_summary.php --lang=bn
php scripts/report_missing_translations.php --lang=bn --output=missing_bn.json

# 4. View sync reports in the sync_reports/ folder (if created)
