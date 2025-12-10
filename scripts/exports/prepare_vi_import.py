#!/usr/bin/env python3
"""
Prepare an import-ready CSV from `remaining_vi_for_translation.csv`.
Output file: `scripts/exports/vi_import_ready.csv` with columns: hadith_id,localization_code,translation_text
By default uses `en_translation` if available, else `arabic_text` as a draft translation.
"""
import os, csv, sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT = os.path.join(BASE, 'scripts', 'exports', 'remaining_vi_for_translation.csv')
OUTPUT = os.path.join(BASE, 'scripts', 'exports', 'vi_import_ready.csv')

if not os.path.isfile(INPUT):
    print('Input not found:', INPUT)
    sys.exit(1)

count = 0
with open(INPUT, newline='', encoding='utf-8') as inf, open(OUTPUT, 'w', newline='', encoding='utf-8') as outf:
    reader = csv.DictReader(inf)
    writer = csv.writer(outf)
    writer.writerow(['hadith_id', 'localization_code', 'translation_text'])
    for r in reader:
        hid = r.get('hadith_id')
        if not hid:
            continue
        en = r.get('en_translation','').strip()
        ar = r.get('arabic_text','').strip()
        text = en or ar
        # Avoid empty translations; still write rows so translator can fill
        writer.writerow([hid, 'vi', text])
        count += 1

print(f'Wrote {count} rows -> {OUTPUT}')
