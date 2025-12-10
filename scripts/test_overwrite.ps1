# Test script for overwrite behavior (PowerShell)
# This runs a dry-run first then performs a controlled overwrite for bn sample of 5 items.
# Usage: .\scripts\test_overwrite.ps1

python .\scripts\sync_missing_translations.py --languages bn --sample 5 --dry-run

# After verifying output, perform overwrite (requires explicit confirm)
# This will update the found items. Replace --sample with --limit for larger sets.
python .\scripts\sync_missing_translations.py --languages bn --sample 5 --overwrite --confirm


# You can also call the artisan command (non-blocking) but make sure to pass --confirm
php artisan sync:missing-translations --languages=bn --sample=5 --overwrite --confirm
