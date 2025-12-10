# ✅ ESSENTIAL FILES ONLY - Quick Reference

## Main Import Script
**`import_all.py`** is the ONLY script you need to run!

## Usage
```powershell
cd f:\backup-hadith-api\hadith-api\scripts
python import_all.py
```

Or use the PowerShell launcher:
```powershell
.\import_all.ps1
```

## All Essential Files (12 files only)

### Must Have (Core)
1. ✅ `import_all.py` - Main orchestrator
2. ✅ `config.py` - Configuration
3. ✅ `utils.py` - Utilities

### Must Have (Steps)
4. ✅ `step0_setup_database.py`
5. ✅ `step1_generate_complete_chapters.py`
6. ✅ `step2_import_metadata_from_csv.py`
7. ✅ `step4_import_hadiths_fawaz.py`
8. ✅ `step5_import_hadeethenc_complete.py`

### Optional (Utilities)
9. ✅ `check_languages.py`
10. ✅ `reset_database.py`
11. ✅ `requirements.txt`
12. ✅ `import_all.ps1`

## Everything Else is Unnecessary!

### Files to Remove (~200+ files)
- ❌ All `test_*.py` files (50+)
- ❌ All `check_*.py` files except `check_languages.py` (60+)
- ❌ All `debug_*.py` files (15+)
- ❌ All `verify_*.py` files (15+)
- ❌ All `fix_*.py` files (10+)
- ❌ All old import variations (40+)
- ❌ All `.php` files (18)
- ❌ All `.md` files in scripts/ (5+)
- ❌ Other utilities and helpers (30+)

## Run Cleanup

To automatically remove all unnecessary files:

```powershell
cd f:\backup-hadith-api\hadith-api\scripts
.\cleanup_unused_files.ps1
```

The script will:
1. Show exactly what will be deleted (categorized)
2. Ask for your confirmation
3. Delete only unnecessary files
4. Keep all 12 essential files

## Current Statistics

**Before Cleanup:**
- Python files: 173
- PHP files: 18
- Total: 191+ files

**After Cleanup:**
- Python files: 10
- PowerShell: 2
- Total: 12 essential files only

**Reduction: ~94% fewer files!**

## What Gets Deleted?

See `CLEANUP_SUMMARY.md` for detailed list of all files that will be removed.

## Safety

✅ **Safe to delete** - All test/check/debug files
✅ **No data loss** - Database and CSV exports are safe
✅ **Reversible** - Everything is in your backup
✅ **Confirmed** - Script asks before deleting

---

**TL;DR**: Run `cleanup_unused_files.ps1` to remove ~180 unnecessary test/check/debug files and keep only the 12 essential files needed by `import_all.py`.
