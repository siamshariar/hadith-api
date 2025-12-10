#!/usr/bin/env python3
import os
import csv
import mysql.connector
from config import DB_CONFIG, LOCALIZATION_MAP

OUT_DIR = os.path.join(os.path.dirname(__file__), 'missing_translations')
os.makedirs(OUT_DIR, exist_ok=True)

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM hadiths')
    total = cur.fetchone()[0]
    print(f'Total hadiths: {total}')

    for lang in LOCALIZATION_MAP.keys():
        cur.execute('SELECT COUNT(*) FROM hadith_translations WHERE localization_code=%s', (lang,))
        cnt = cur.fetchone()[0]
        if cnt >= total:
            print(f"Skipping {lang} - full coverage ({cnt}/{total})")
            continue

        cur.execute('SELECT id FROM hadiths WHERE id NOT IN (SELECT hadith_id FROM hadith_translations WHERE localization_code=%s)', (lang,))
        rows = [r[0] for r in cur.fetchall()]

        out_path = os.path.join(OUT_DIR, f'missing_{lang}.csv')
        with open(out_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['hadith_id'])
            for hid in rows:
                writer.writerow([hid])

        print(f'Wrote {len(rows)} missing IDs for {lang} -> {out_path}')

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
