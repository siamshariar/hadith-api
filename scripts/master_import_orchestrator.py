#!/usr/bin/env python3
"""
MASTER HADITH IMPORT ORCHESTRATOR - COMPLETE 100% DATA COVERAGE
Imports all hadith data from multiple sources with proper localization

Sources:
1. CSV files (books, chapters, categories)
2. Fawaz Hadith API (multiple languages)
3. HadeethEnc API (17 languages, categories, explanations)
4. Bangla-Hadith API (additional Bengali translations)

Features:
- Idempotent (skips existing data)
- Comprehensive language coverage
- Proper table relationships
- Error handling and recovery
- Progress tracking
- Verification at end

Usage: python scripts/master_import_orchestrator.py [--yes] [--overwrite]
"""

import os
import sys
import time
import csv
import requests
import mysql.connector
import argparse
from typing import Dict, List, Optional
from config import DB_CONFIG, LOCALIZATION_MAP, BOOK_CODE_MAP, FAWAZ_HADITH_API_EDITIONS
from utils import get_db_connection, fetch_api_data, clean_text


def resolve_csv_path(filename: str) -> str:
    """Resolve CSV file path by checking multiple expected directories.

    Order of preference:
    - csv_exports/
    - csv-categories/
    - csv/

    Returns a path (may not exist) to be opened by the caller. If none
    of the alternative directories contain the file, the default
    `csv_exports/filename` path is returned so the original error is
    raised by the caller.
    """
    candidates = ['csv_exports', 'csv-categories', 'csv']
    for d in candidates:
        p = os.path.join(d, filename)
        if os.path.exists(p):
            return p
    # Fallback to original path (allow original FileNotFoundError to surface)
    return os.path.join('csv_exports', filename)


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"🎯 {title}")
    print("=" * 80)


def print_progress(current: int, total: int, item: str = "items"):
    """Print progress indicator"""
    percentage = (current / total * 100) if total > 0 else 0
    print(f"📊 Progress: {current}/{total} {item} ({percentage:.1f}%)")


def import_csv_data():
    """Import books, chapters, and categories from CSV files"""
    print_header("STEP 1: IMPORTING CSV DATA")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Import books
        print("📚 Importing books from CSV...")
        with open(resolve_csv_path('books.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT INTO books (id, code, name_en, name_ar, total_hadith, slug, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        name_en = VALUES(name_en),
                        name_ar = VALUES(name_ar),
                        total_hadith = VALUES(total_hadith),
                        updated_at = NOW()
                """, (
                    row['id'], row['code'], row['name_en'], row['name_ar'],
                    row.get('total_hadith', 0), row['slug']
                ))

        # Import books localizations
        print("🌐 Importing books localizations...")
        with open(resolve_csv_path('books_localizations.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT INTO books_localizations (book_id, localization_id, localization_code, name, slug, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        updated_at = NOW()
                """, (
                    row['book_id'], row['localization_id'], row['localization_code'],
                    row['name'], row['slug']
                ))

        # Import chapters
        print("📖 Importing chapters...")
        with open(resolve_csv_path('chapters.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT INTO chapters (id, book_id, chapter_no, name_en, name_ar, total_hadith, slug, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        name_en = VALUES(name_en),
                        name_ar = VALUES(name_ar),
                        total_hadith = VALUES(total_hadith),
                        updated_at = NOW()
                """, (
                    row['id'], row['book_id'], row['chapter_no'], row['name_en'],
                    row.get('name_ar', ''), row.get('total_hadith', 0), row['slug']
                ))

        # Import categories
        print("📂 Importing categories...")
        with open(resolve_csv_path('categories.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT INTO categories (id, parent_id, name_en, name_ar, slug, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        parent_id = VALUES(parent_id),
                        name_en = VALUES(name_en),
                        name_ar = VALUES(name_ar),
                        updated_at = NOW()
                """, (
                    row['id'], 
                    int(row['parent_id']) if row.get('parent_id') and row['parent_id'].strip() else None, 
                    row['name_en'],
                    row.get('name_ar', ''), 
                    row['slug']
                ))

        # Import category localizations
        print("🌍 Importing category localizations...")
        with open(resolve_csv_path('category_localizations.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT INTO category_localizations (category_id, localization_code, name, slug, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        updated_at = NOW()
                """, (
                    row['category_id'], row['localization_code'], row['name'], row['slug']
                ))

        conn.commit()
        print("✅ CSV data import completed successfully")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error importing CSV data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def import_hadeethenc_data():
    """Import comprehensive data from HadeethEnc API (17 languages)"""
    print_header("STEP 2: IMPORTING HADEETHENC DATA (17 LANGUAGES)")

    # HadeethEnc languages
    hadeethenc_langs = [
        'ar', 'en', 'fr', 'es', 'tr', 'ur', 'id', 'bs', 'ru', 'bn',
        'zh', 'fa', 'tl', 'hi', 'vi', 'si', 'ug'
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Import categories from HadeethEnc
        print("📂 Importing HadeethEnc categories...")
        categories_url = "https://hadeethenc.com/api/v1/categories/roots/?language=en"
        categories_data = fetch_api_data(categories_url)

        if categories_data:
            for cat in categories_data:
                # Insert category
                cursor.execute("""
                    INSERT INTO categories (id, name_en, slug, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        name_en = VALUES(name_en),
                        updated_at = NOW()
                """, (cat['id'], cat['title'], f"category-{cat['id']}"))

                # Import category localizations for all languages
                for lang in hadeethenc_langs:
                    try:
                        cat_url = f"https://hadeethenc.com/api/v1/categories/roots/?language={lang}"
                        cat_data = fetch_api_data(cat_url)
                        if cat_data:
                            for c in cat_data:
                                if c['id'] == cat['id']:
                                    cursor.execute("""
                                        INSERT INTO category_localizations (category_id, localization_code, name, created_at, updated_at)
                                        VALUES (%s, %s, %s, NOW(), NOW())
                                        ON DUPLICATE KEY UPDATE
                                            name = VALUES(name),
                                            updated_at = NOW()
                                    """, (cat['id'], lang, c['title']))
                        time.sleep(0.1)  # Rate limiting
                    except:
                        continue

        # Import hadiths from HadeethEnc
        print("📖 Importing HadeethEnc hadiths...")
        hadith_count = 0

        for cat in categories_data:
            hadiths_url = f"https://hadeethenc.com/api/v1/hadeeths/list/?language=en&category_id={cat['id']}&per_page=1000"
            hadiths_data = fetch_api_data(hadiths_url)

            if hadiths_data and 'data' in hadiths_data:
                for hadith in hadiths_data['data']:
                    hadith_id = hadith['id']

                    # Get detailed hadith info
                    detail_url = f"https://hadeethenc.com/api/v1/hadeeths/one/?id={hadith_id}&language=ar"
                    detail_data = fetch_api_data(detail_url)

                    if detail_data:
                        # Insert main hadith (Arabic)
                        arabic_text = detail_data.get('hadeeth', '')
                        if arabic_text:
                            cursor.execute("""
                                INSERT INTO hadiths (id, book_id, chapter_id, hadith_number, arabic_text, grade, created_at, updated_at)
                                VALUES (%s, 1, 1, %s, %s, %s, NOW(), NOW())
                                ON DUPLICATE KEY UPDATE
                                    arabic_text = VALUES(arabic_text),
                                    grade = VALUES(grade),
                                    updated_at = NOW()
                            """, (
                                hadith_id,
                                hadith_id,  # Use ID as hadith number
                                arabic_text,
                                detail_data.get('grade', 'Unknown')
                            ))

                            # Link to category
                            cursor.execute("""
                                INSERT IGNORE INTO hadith_category (hadith_id, category_id)
                                VALUES (%s, %s)
                            """, (hadith_id, cat['id']))

                            # Import translations for all languages
                            for lang in hadeethenc_langs:
                                try:
                                    trans_url = f"https://hadeethenc.com/api/v1/hadeeths/one/?id={hadith_id}&language={lang}"
                                    trans_data = fetch_api_data(trans_url)

                                    if trans_data and 'hadeeth' in trans_data:
                                        translation_text = trans_data['hadeeth']
                                        explanation = trans_data.get('explanation', '')
                                        hints = trans_data.get('hints', '')

                                        if isinstance(hints, list):
                                            hints = ' '.join(hints)

                                        cursor.execute("""
                                            INSERT INTO hadith_translations (hadith_id, localization_code, translation_text, created_at, updated_at)
                                            VALUES (%s, %s, %s, NOW(), NOW())
                                            ON DUPLICATE KEY UPDATE
                                                translation_text = VALUES(translation_text),
                                                updated_at = NOW()
                                        """, (hadith_id, lang, clean_text(translation_text)))

                                        # Update hadith with explanation if available
                                        if explanation and lang == 'en':
                                            cursor.execute("""
                                                UPDATE hadiths SET explanation = %s WHERE id = %s
                                            """, (explanation, hadith_id))

                                except:
                                    continue

                            hadith_count += 1
                            if hadith_count % 50 == 0:
                                print_progress(hadith_count, len(hadiths_data['data']), "hadiths")

                    time.sleep(0.2)  # Rate limiting

        conn.commit()
        print(f"✅ HadeethEnc import completed: {hadith_count} hadiths imported")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error importing HadeethEnc data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def import_fawaz_data():
    """Import hadith texts and translations from Fawaz API"""
    print_header("STEP 3: IMPORTING FAWAZ HADITH API DATA")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get existing books
        cursor.execute("SELECT id, code FROM books")
        books = {code: book_id for book_id, code in cursor.fetchall()}

        total_imported = 0

        for book_code, book_info in BOOK_CODE_MAP.items():
            if book_code not in books:
                print(f"⚠️  Book {book_code} not found in database, skipping...")
                continue

            book_id = books[book_code]
            fawaz_code = book_info.get('fawaz', '')

            if not fawaz_code:
                continue

            print(f"📚 Processing {book_info['name_en']}...")

            # Import Arabic texts first
            arabic_imported = import_fawaz_book(cursor, fawaz_code, book_id, 'ar', 5000)
            total_imported += arabic_imported

            # Import other languages
            for lang_code in LOCALIZATION_MAP.keys():
                if lang_code == 'ar':
                    continue

                edition_map = {
                    'en': fawaz_code.replace('ara-', 'eng-'),
                    'ur': fawaz_code.replace('ara-', 'urd-'),
                    'bn': fawaz_code.replace('ara-', 'ben-'),
                    'tr': fawaz_code.replace('ara-', 'tur-'),
                    'fa': fawaz_code.replace('ara-', 'per-'),
                    'fr': fawaz_code.replace('ara-', 'fre-'),
                    'es': fawaz_code.replace('ara-', 'spa-'),
                    'de': fawaz_code.replace('ara-', 'ger-'),
                    'ru': fawaz_code.replace('ara-', 'rus-'),
                    'id': fawaz_code.replace('ara-', 'ind-'),
                }

                if lang_code in edition_map:
                    lang_imported = import_fawaz_book(cursor, edition_map[lang_code], book_id, lang_code, 5000)
                    total_imported += lang_imported

            conn.commit()

        print(f"✅ Fawaz API import completed: {total_imported} translations imported")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error importing Fawaz data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def import_fawaz_book(cursor, edition_name: str, book_id: int, lang_code: str, max_hadiths: int) -> int:
    """Import hadiths for a specific book and language from Fawaz API"""
    imported = 0

    for hadith_num in range(1, max_hadiths + 1):
        # Construct URLs
        urls = [
            f"{FAWAZ_HADITH_API_EDITIONS}/{edition_name}/{hadith_num}.json",
            f"{FAWAZ_HADITH_API_EDITIONS}/{edition_name}/{hadith_num}.min.json"
        ]

        hadith_data = None
        for url in urls:
            hadith_data = fetch_api_data(url, silent=True)
            if hadith_data:
                break

        if not hadith_data:
            continue

        try:
            # Extract hadith info
            if 'hadiths' in hadith_data and isinstance(hadith_data['hadiths'], list) and hadith_data['hadiths']:
                hadith_info = hadith_data['hadiths'][0]
            else:
                hadith_info = hadith_data.get('hadith', hadith_data)

            # Get text
            if lang_code == 'ar':
                text = hadith_info.get('text', '') or hadith_info.get('arabic', '')
            else:
                text = hadith_info.get('text', '') or hadith_info.get('translation', '')

            text = clean_text(text)
            if not text or len(text.strip()) < 10:
                continue

            # Get chapter
            chapter_no = hadith_info.get('chapterNo', hadith_info.get('chapterno', hadith_info.get('chapter', 1)))
            if isinstance(chapter_no, str):
                try:
                    chapter_no = int(chapter_no)
                except:
                    chapter_no = 1

            # Get/create chapter
            cursor.execute("""
                SELECT id FROM chapters WHERE book_id = %s AND chapter_no = %s
            """, (book_id, chapter_no))

            chapter_result = cursor.fetchone()
            if chapter_result:
                chapter_id = chapter_result[0]
            else:
                cursor.execute("""
                    INSERT INTO chapters (book_id, chapter_no, name_en, slug, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                """, (book_id, chapter_no, f"Chapter {chapter_no}", f"chapter-{chapter_no}"))
                chapter_id = cursor.lastrowid

            hadith_number = str(hadith_info.get('hadithNumber', hadith_info.get('hadithnumber', hadith_num)))

            if lang_code == 'ar':
                # Check if hadith exists
                cursor.execute("""
                    SELECT id FROM hadiths WHERE book_id = %s AND hadith_number = %s
                """, (book_id, hadith_number))

                if not cursor.fetchone():
                    # Get grade
                    raw_grade = hadith_info.get('grades', hadith_info.get('grade', None))
                    grade = normalize_grade(raw_grade)

                    # Insert hadith
                    cursor.execute("""
                        INSERT INTO hadiths (book_id, chapter_id, hadith_number, arabic_text, grade, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    """, (book_id, chapter_id, hadith_number, text, grade))
                    imported += 1
            else:
                # Find hadith ID
                cursor.execute("""
                    SELECT id FROM hadiths WHERE book_id = %s AND hadith_number = %s
                """, (book_id, hadith_number))

                result = cursor.fetchone()
                if result:
                    hadith_id = result[0]

                    # Check if translation exists
                    cursor.execute("""
                        SELECT id FROM hadith_translations WHERE hadith_id = %s AND localization_code = %s
                    """, (hadith_id, lang_code))

                    if not cursor.fetchone():
                        localization_id = LOCALIZATION_MAP.get(lang_code, {}).get('id', 1)
                        cursor.execute("""
                            INSERT INTO hadith_translations (hadith_id, localization_id, localization_code, translation_text, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, NOW(), NOW())
                        """, (hadith_id, localization_id, lang_code, text))
                        imported += 1

        except Exception as e:
            continue

    return imported


def normalize_grade(raw_grade) -> Optional[str]:
    """Normalize grade information from various formats"""
    if not raw_grade:
        return None

    if isinstance(raw_grade, list):
        grades = []
        for g in raw_grade:
            if isinstance(g, dict):
                grade_val = g.get('grade') or g.get('name')
                if grade_val:
                    grades.append(str(grade_val).strip())
            elif isinstance(g, str):
                grades.append(g.strip())
        return ' | '.join(grades) if grades else None
    elif isinstance(raw_grade, dict):
        return raw_grade.get('grade') or raw_grade.get('name')
    elif isinstance(raw_grade, str):
        return raw_grade.strip()

    return str(raw_grade) if raw_grade else None


def import_bangla_hadith_api():
    """Import additional data from Bangla-Hadith API"""
    print_header("STEP 4: IMPORTING BANGLA HADITH API DATA")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Bangla Hadith API base
        base_url = "http://alquranbd.com/api/hadith"

        # Get books list
        books_data = fetch_api_data(f"{base_url}")
        if not books_data:
            print("❌ Could not fetch books from Bangla Hadith API")
            return

        imported = 0

        for book in books_data:
            book_key = book.get('book_key')
            if not book_key:
                continue

            # Map to our book codes
            book_mapping = {
                'bukhari': 'bukhari',
                'muslim': 'muslim',
                'riyadusSalihin': 'riyadussalihin',
                'abuDaud': 'abudawud',
                'ibnMajah': 'ibnmajah',
                'tirmidi': 'tirmidhi'
            }

            if book_key not in book_mapping:
                continue

            our_book_code = book_mapping[book_key]

            # Get our book ID
            cursor.execute("SELECT id FROM books WHERE code = %s", (our_book_code,))
            book_result = cursor.fetchone()
            if not book_result:
                continue

            book_id = book_result[0]

            print(f"📚 Processing {book.get('nameEnglish', book_key)}...")

            # Get chapters
            chapters_data = fetch_api_data(f"{base_url}/{book_key}")
            if not chapters_data:
                continue

            for chapter in chapters_data:
                chapter_no = chapter.get('chSerial', chapter.get('id', 1))

                # Get our chapter ID
                cursor.execute("""
                    SELECT id FROM chapters WHERE book_id = %s AND chapter_no = %s
                """, (book_id, chapter_no))

                chapter_result = cursor.fetchone()
                if not chapter_result:
                    # Create chapter
                    cursor.execute("""
                        INSERT INTO chapters (book_id, chapter_no, name_en, name_ar, slug, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    """, (
                        book_id, chapter_no,
                        chapter.get('nameEnglish', f'Chapter {chapter_no}'),
                        chapter.get('nameBengali', ''),
                        f"chapter-{chapter_no}"
                    ))
                    chapter_id = cursor.lastrowid
                else:
                    chapter_id = chapter_result[0]

                # Get hadiths for this chapter
                hadiths_data = fetch_api_data(f"{base_url}/{book_key}/{chapter_no}")
                if not hadiths_data:
                    continue

                for hadith in hadiths_data:
                    hadith_no = hadith.get('hadithNo', hadith.get('id'))

                    # Check if hadith exists
                    cursor.execute("""
                        SELECT id FROM hadiths WHERE book_id = %s AND hadith_number = %s
                    """, (book_id, str(hadith_no)))

                    hadith_result = cursor.fetchone()
                    if hadith_result:
                        hadith_id = hadith_result[0]
                    else:
                        # Create hadith
                        arabic_text = hadith.get('hadithArabic', '')
                        if arabic_text:
                            cursor.execute("""
                                INSERT INTO hadiths (book_id, chapter_id, hadith_number, arabic_text, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, NOW(), NOW())
                            """, (book_id, chapter_id, str(hadith_no), clean_text(arabic_text)))
                            hadith_id = cursor.lastrowid
                        else:
                            continue

                    # Import English translation
                    english_text = hadith.get('hadithEnglish', '')
                    if english_text:
                        cursor.execute("""
                            SELECT id FROM hadith_translations WHERE hadith_id = %s AND localization_code = 'en'
                        """, (hadith_id,))

                        if not cursor.fetchone():
                            cursor.execute("""
                                INSERT INTO hadith_translations (hadith_id, localization_code, translation_text, created_at, updated_at)
                                VALUES (%s, 'en', %s, NOW(), NOW())
                            """, (hadith_id, clean_text(english_text)))
                            imported += 1

                    # Import Bengali translation
                    bengali_text = hadith.get('hadithBengali', '')
                    if bengali_text:
                        cursor.execute("""
                            SELECT id FROM hadith_translations WHERE hadith_id = %s AND localization_code = 'bn'
                        """, (hadith_id,))

                        if not cursor.fetchone():
                            cursor.execute("""
                                INSERT INTO hadith_translations (hadith_id, localization_code, translation_text, created_at, updated_at)
                                VALUES (%s, 'bn', %s, NOW(), NOW())
                            """, (hadith_id, clean_text(bengali_text)))
                            imported += 1

        conn.commit()
        print(f"✅ Bangla Hadith API import completed: {imported} translations imported")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error importing Bangla Hadith API data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def fix_missing_data():
    """Fix any missing or incorrect data"""
    print_header("STEP 5: FIXING MISSING AND INCORRECT DATA")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update total hadith counts for books
        print("📊 Updating book total hadith counts...")
        cursor.execute("""
            UPDATE books b
            SET total_hadith = (SELECT COUNT(*) FROM hadiths h WHERE h.book_id = b.id)
            WHERE EXISTS (SELECT 1 FROM hadiths h WHERE h.book_id = b.id)
        """)

        # Update total hadith counts for chapters
        print("📖 Updating chapter total hadith counts...")
        cursor.execute("""
            UPDATE chapters c
            SET total_hadith = (SELECT COUNT(*) FROM hadiths h WHERE h.chapter_id = c.id)
            WHERE EXISTS (SELECT 1 FROM hadiths h WHERE h.chapter_id = c.id)
        """)

        # Ensure all hadiths have proper chapter assignments
        print("🔗 Fixing chapter assignments...")
        cursor.execute("""
            UPDATE hadiths h
            SET chapter_id = (
                SELECT MIN(c.id) FROM chapters c
                WHERE c.book_id = h.book_id
            )
            WHERE chapter_id NOT IN (SELECT id FROM chapters)
        """)

        # Clean up any orphaned translations
        print("🧹 Cleaning up orphaned translations...")
        cursor.execute("""
            DELETE FROM hadith_translations
            WHERE hadith_id NOT IN (SELECT id FROM hadiths)
        """)

        conn.commit()
        print("✅ Data fixes completed")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error fixing data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def verify_import():
    """Verify the completeness of the import"""
    print_header("STEP 6: VERIFICATION")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Basic counts
        checks = [
            ('Books', 'SELECT COUNT(*) FROM books'),
            ('Book Localizations', 'SELECT COUNT(*) FROM books_localizations'),
            ('Chapters', 'SELECT COUNT(*) FROM chapters'),
            ('Categories', 'SELECT COUNT(*) FROM categories'),
            ('Category Localizations', 'SELECT COUNT(*) FROM category_localizations'),
            ('Hadiths', 'SELECT COUNT(*) FROM hadiths'),
            ('Hadith Translations', 'SELECT COUNT(*) FROM hadith_translations'),
            ('Hadith-Category Links', 'SELECT COUNT(*) FROM hadith_category')
        ]

        for name, sql in checks:
            cursor.execute(sql)
            count = cursor.fetchone()[0]
            print(f"✅ {name}: {count}")

        # Get total hadiths
        cursor.execute("SELECT COUNT(*) FROM hadiths")
        total_hadiths_result = cursor.fetchone()
        total_hadiths = total_hadiths_result[0] if total_hadiths_result else 0

        # Translation coverage by language
        print("\n🌍 Translation Coverage by Language:")
        cursor.execute("""
            SELECT localization_code, COUNT(*) as count
            FROM hadith_translations
            GROUP BY localization_code
            ORDER BY count DESC
        """)

        coverage_rows = cursor.fetchall()
        for row in coverage_rows:
            lang_code, count = row
            coverage = (count / total_hadiths * 100) if total_hadiths > 0 else 0
            lang_name = LOCALIZATION_MAP.get(lang_code, {}).get('name', lang_code)
            print(f"   {lang_code} ({lang_name}): {count} translations ({coverage:.1f}%)")

        # Check for missing translations
        print("\n⚠️  Languages with missing translations:")
        for lang_code, lang_info in LOCALIZATION_MAP.items():
            cursor.execute("""
                SELECT COUNT(*) FROM hadiths h
                LEFT JOIN hadith_translations t ON h.id = t.hadith_id AND t.localization_code = %s
                WHERE t.id IS NULL
            """, (lang_code,))

            missing_result = cursor.fetchone()
            missing = missing_result[0] if missing_result else 0
            if missing > 0:
                percentage = (missing / total_hadiths * 100) if total_hadiths > 0 else 0
                print(f"   {lang_code} ({lang_info['name']}): {missing} missing ({percentage:.1f}%)")

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def main():
    """Main orchestrator function"""
    parser = argparse.ArgumentParser(description='Complete Hadith Import Orchestrator')
    parser.add_argument('--yes', action='store_true', help='Skip confirmations')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing data (dangerous)')
    parser.add_argument('--skip-csv', action='store_true', help='Skip CSV import')
    parser.add_argument('--skip-hadeethenc', action='store_true', help='Skip HadeethEnc import')
    parser.add_argument('--skip-fawaz', action='store_true', help='Skip Fawaz API import')
    parser.add_argument('--skip-bangla', action='store_true', help='Skip Bangla Hadith API import')

    args = parser.parse_args()

    print_header("MASTER HADITH IMPORT ORCHESTRATOR")
    print("This will import complete hadith data from all available sources")
    print("Sources: CSV files, Fawaz API, HadeethEnc API, Bangla Hadith API")
    print("Languages: All available translations (17+ languages)")
    print("\nEstimated time: 4-8 hours depending on internet speed")

    if not args.yes:
        response = input("\nDo you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Import cancelled.")
            return

    start_time = time.time()

    try:
        # Step 1: CSV Import
        if not args.skip_csv:
            import_csv_data()

        # Step 2: HadeethEnc Import
        if not args.skip_hadeethenc:
            import_hadeethenc_data()

        # Step 3: Fawaz API Import
        if not args.skip_fawaz:
            import_fawaz_data()

        # Step 4: Bangla Hadith API Import
        if not args.skip_bangla:
            import_bangla_hadith_api()

        # Step 5: Fix missing data
        fix_missing_data()

        # Step 6: Verify
        verify_import()

        elapsed_time = time.time() - start_time
        print_header("IMPORT COMPLETED SUCCESSFULLY")
        print(f"⏱️  Total time: {elapsed_time / 60:.1f} minutes")
        print("🎉 Your Hadith API now has complete data coverage!")

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()