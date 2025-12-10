#!/usr/bin/env python3
"""
CHECK TRANSLATION COVERAGE - Identify languages needing 100% coverage
"""

import mysql.connector
from config import DB_CONFIG, LOCALIZATION_MAP

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Get total hadiths
    cursor.execute('SELECT COUNT(*) FROM hadiths')
    total_hadiths = cursor.fetchone()[0]

    # Check translation coverage by language
    cursor.execute('SELECT localization_code, COUNT(*) FROM hadith_translations GROUP BY localization_code ORDER BY COUNT(*) DESC')
    existing_translations = {row[0]: row[1] for row in cursor.fetchall()}

    print('🌍 CURRENT TRANSLATION COVERAGE:')
    missing_langs = []
    for lang_code, lang_info in LOCALIZATION_MAP.items():
        count = existing_translations.get(lang_code, 0)
        coverage = (count / total_hadiths * 100) if total_hadiths > 0 else 0
        status = '✅' if coverage > 95 else '🟡' if coverage > 50 else '❌'
        print(f'   {status} {lang_info["name"]} ({lang_code}): {count}/{total_hadiths} ({coverage:.1f}%)')
        if coverage < 95:
            missing_langs.append(lang_code)

    print(f'\n🎯 MISSING LANGUAGES: {len(missing_langs)}')
    for lang in missing_langs:
        print(f'   - {LOCALIZATION_MAP[lang]["name"]} ({lang})')

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()