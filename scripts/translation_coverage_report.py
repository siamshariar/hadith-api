#!/usr/bin/env python3
import json
import mysql.connector
from config import DB_CONFIG, LOCALIZATION_MAP

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM hadiths')
    total = cur.fetchone()[0]

    report = {'total_hadiths': total, 'languages': {}}

    for lang in LOCALIZATION_MAP.keys():
        cur.execute('SELECT COUNT(*) FROM hadith_translations WHERE localization_code=%s', (lang,))
        cnt = cur.fetchone()[0]

        cur.execute('SELECT id FROM hadiths WHERE id NOT IN (SELECT hadith_id FROM hadith_translations WHERE localization_code=%s) LIMIT 20', (lang,))
        missing = [r[0] for r in cur.fetchall()]

        report['languages'][lang] = {
            'translations_count': cnt,
            'missing_sample_count': len(missing),
            'missing_sample': missing
        }

    cur.close()
    conn.close()

    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
