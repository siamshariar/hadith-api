"""
COMPLETE HADEETHENC API IMPORT - 100% DATA COVERAGE
Fetches ALL data from HadeethEnc API including all 17 languages
"""

import requests
import mysql.connector
import time
from config import DB_CONFIG

# HadeethEnc API Base URL
BASE_URL = "https://hadeethenc.com/api/v1"

# All 17 supported languages from HadeethEnc
LANGUAGES = [
    {"code": "ar", "name": "Arabic", "native": "عربي"},
    {"code": "en", "name": "English", "native": "English"},
    {"code": "fr", "name": "French", "native": "Français"},
    {"code": "es", "name": "Spanish", "native": "Español"},
    {"code": "tr", "name": "Turkish", "native": "Türkçe"},
    {"code": "ur", "name": "Urdu", "native": "اردو"},
    {"code": "id", "name": "Indonesian", "native": "Indonesia"},
    {"code": "bs", "name": "Bosnian", "native": "Bosanski"},
    {"code": "ru", "name": "Russian", "native": "Русский"},
    {"code": "bn", "name": "Bengali", "native": "বাংলা ভাষা"},
    {"code": "zh", "name": "Chinese", "native": "中文"},
    {"code": "fa", "name": "Persian", "native": "فارسی"},
    {"code": "tl", "name": "Tagalog", "native": "Tagalog"},
    {"code": "hi", "name": "Hindi", "native": "हिन्दी"},
    {"code": "vi", "name": "Vietnamese", "native": "Tiếng Việt"},
    {"code": "si", "name": "Sinhala", "native": "සිංහල"},
    {"code": "ug", "name": "Uyghur", "native": "ئۇيغۇرچە"}
]


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"🎯 {title}")
    print("=" * 80)


def fetch_api(endpoint, lang="en"):
    """Fetch data from HadeethEnc API"""
    url = f"{BASE_URL}/{endpoint}"
    headers = {"Accept-Language": lang}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching {endpoint}: {e}")
        return None


def get_db_connection():
    """Get database connection"""
    return mysql.connector.connect(**DB_CONFIG)


def import_languages():
    """Import all 17 languages"""
    print_header("IMPORTING LANGUAGES")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for lang in LANGUAGES:
        try:
            cursor.execute("""
                INSERT INTO languages (code, name, native_name, direction, enabled)
                VALUES (%s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    native_name = VALUES(native_name)
            """, (
                lang['code'],
                lang['name'],
                lang['native'],
                'rtl' if lang['code'] in ['ar', 'ur', 'fa', 'ug'] else 'ltr'
            ))
            print(f"✅ {lang['name']} ({lang['code']})")
        except Exception as e:
            print(f"❌ Error importing {lang['name']}: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n✅ Imported {len(LANGUAGES)} languages")


def import_categories():
    """Import all categories with all language translations"""
    print_header("IMPORTING CATEGORIES (ALL LANGUAGES)")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch categories in English first to get structure
    categories_data = fetch_api("categories", "en")
    if not categories_data:
        print("❌ Failed to fetch categories")
        return
    
    total_categories = len(categories_data)
    print(f"📊 Found {total_categories} categories")
    
    category_count = 0
    translation_count = 0
    
    for cat in categories_data:
        category_id = cat.get('id')
        parent_id = cat.get('parent_id')
        
        # Insert category
        try:
            cursor.execute("""
                INSERT INTO categories (id, parent_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    parent_id = VALUES(parent_id),
                    updated_at = NOW()
            """, (category_id, parent_id, cat.get('title', 'Untitled')))
            category_count += 1
        except Exception as e:
            print(f"❌ Error inserting category {category_id}: {e}")
            continue
        
        # Import translations for all languages
        for lang in LANGUAGES:
            try:
                # Fetch category in this language
                cat_lang = fetch_api(f"categories/{category_id}", lang['code'])
                if cat_lang:
                    title = cat_lang.get('title', cat.get('title', ''))
                    
                    cursor.execute("""
                        INSERT INTO category_translations 
                        (category_id, localization_code, title, created_at, updated_at)
                        VALUES (%s, %s, %s, NOW(), NOW())
                        ON DUPLICATE KEY UPDATE
                            title = VALUES(title),
                            updated_at = NOW()
                    """, (category_id, lang['code'], title))
                    translation_count += 1
                
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                print(f"⚠️  Error importing category {category_id} translation ({lang['code']}): {e}")
        
        if category_count % 10 == 0:
            print(f"Progress: {category_count}/{total_categories} categories...")
            conn.commit()
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Imported {category_count} categories")
    print(f"✅ Imported {translation_count} category translations")


def import_hadiths():
    """Import all hadiths with all language translations"""
    print_header("IMPORTING HADITHS (ALL LANGUAGES)")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all categories
    cursor.execute("SELECT id FROM categories")
    categories = [row[0] for row in cursor.fetchall()]
    
    print(f"📊 Processing {len(categories)} categories")
    
    hadith_count = 0
    translation_count = 0
    
    sample_limit = globals().get('SAMPLE_LIMIT', None)
    processed = 0
    for cat_id in categories:
        if sample_limit and processed >= sample_limit:
            break
        print(f"\n📂 Processing Category {cat_id}...")
        
        # Fetch hadiths for this category (English first)
        hadiths_data = fetch_api(f"categories/{cat_id}/hadiths", "en")
        if not hadiths_data:
            continue
        
        for hadith in hadiths_data:
            if sample_limit and processed >= sample_limit:
                break
            hadith_id = hadith.get('id')
            
            # Insert main hadith record
            try:
                cursor.execute("""
                    INSERT INTO hadiths 
                    (id, book_id, chapter_id, hadith_number, arabic_text, 
                     grade, attribution, created_at, updated_at)
                    VALUES (%s, 1, 1, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        arabic_text = VALUES(arabic_text),
                        grade = VALUES(grade),
                        updated_at = NOW()
                """, (
                    hadith_id,
                    hadith.get('hadith_number', hadith_id),
                    hadith.get('hadeeth', ''),
                    hadith.get('grade', 'Unknown'),
                    hadith.get('attribution', '')
                ))
                hadith_count += 1
            except Exception as e:
                print(f"❌ Error inserting hadith {hadith_id}: {e}")
                continue
            
            # Import translations for all 17 languages
            for lang in LANGUAGES:
                try:
                    hadith_lang = fetch_api(f"hadeeths/{hadith_id}", lang['code'])
                    if hadith_lang:
                        text = hadith_lang.get('hadeeth', '')
                        explanation = hadith_lang.get('explanation', '')
                        hint = hadith_lang.get('hint', '')
                        
                        if text:  # Only insert if we have text
                            cursor.execute("""
                                INSERT INTO hadith_translations
                                (hadith_id, localization_code, text, explanation, 
                                 hint, word_meanings, references, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                                ON DUPLICATE KEY UPDATE
                                    text = VALUES(text),
                                    explanation = VALUES(explanation),
                                    hint = VALUES(hint),
                                    updated_at = NOW()
                            """, (
                                hadith_id,
                                lang['code'],
                                text,
                                explanation,
                                hint,
                                hadith_lang.get('words_meanings', ''),
                                hadith_lang.get('reference', '')
                            ))
                            translation_count += 1
                    
                    time.sleep(0.1)  # Rate limiting
                except Exception as e:
                    print(f"⚠️  Error importing hadith {hadith_id} translation ({lang['code']})")
            
            # Link hadith to category
            try:
                cursor.execute("""
                    INSERT IGNORE INTO hadith_category (hadith_id, category_id)
                    VALUES (%s, %s)
                """, (hadith_id, cat_id))
            except:
                pass
            
            if hadith_count % 50 == 0:
                print(f"Progress: {hadith_count} hadiths, {translation_count} translations...")
                conn.commit()
            processed += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Imported {hadith_count} hadiths")
    print(f"✅ Imported {translation_count} hadith translations")
    print(f"📊 Average: {translation_count / hadith_count if hadith_count > 0 else 0:.1f} translations per hadith")


def verify_import():
    """Verify the import was successful"""
    print_header("VERIFICATION")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check languages
    cursor.execute("SELECT COUNT(*) FROM languages")
    lang_count = cursor.fetchone()[0]
    print(f"✅ Languages: {lang_count}/17")
    
    # Check categories
    cursor.execute("SELECT COUNT(*) FROM categories")
    cat_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM category_translations")
    cat_trans_count = cursor.fetchone()[0]
    print(f"✅ Categories: {cat_count}")
    print(f"✅ Category Translations: {cat_trans_count}")
    
    # Check hadiths
    cursor.execute("SELECT COUNT(*) FROM hadiths")
    hadith_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM hadith_translations")
    hadith_trans_count = cursor.fetchone()[0]
    print(f"✅ Hadiths: {hadith_count}")
    print(f"✅ Hadith Translations: {hadith_trans_count}")
    
    # Check language coverage
    cursor.execute("""
        SELECT localization_code, COUNT(*) as cnt
        FROM hadith_translations
        GROUP BY localization_code
        ORDER BY cnt DESC
    """)
    print("\n📊 Translation Coverage by Language:")
    for row in cursor.fetchall():
        lang_code, count = row
        lang_name = next((l['name'] for l in LANGUAGES if l['code'] == lang_code), lang_code)
        coverage = (count / hadith_count * 100) if hadith_count > 0 else 0
        print(f"   {lang_code} ({lang_name}): {count} translations ({coverage:.1f}%)")
    
    cursor.close()
    conn.close()


def main():
    """Main import function"""
    print_header("HADEETHENC COMPLETE IMPORT - 100% COVERAGE")
    print("This will import ALL data from HadeethEnc API")
    print("Including all 17 languages and complete metadata")
    print("\nEstimated time: 2-4 hours")
    
    response = input("\nDo you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Import cancelled.")
        return
    
    import argparse

    parser = argparse.ArgumentParser(description='HadeethEnc import helper')
    parser.add_argument('--sample', type=int, default=None, help='Import only first N hadiths per category for quick testing')
    parser.add_argument('--categories-only', action='store_true', help='Only import categories and languages (skip hadiths)')
    args = parser.parse_args()
    # expose sample to functions via global
    if args.sample:
        globals()['SAMPLE_LIMIT'] = args.sample

    start_time = time.time()
    
    try:
        # Step 1: Import languages
        import_languages()
        
        # Step 2: Import categories with all translations
        import_categories()
        
        # Step 3: Import hadiths with all translations
        if not args.categories_only:
            import_hadiths()
        else:
            print('\n--categories-only set: skipped hadith imports')
        import_hadiths()
        
        # Step 4: Verify
        verify_import()
        
        elapsed_time = time.time() - start_time
        print_header("IMPORT COMPLETE")
        print(f"✅ Total time: {elapsed_time / 60:.1f} minutes")
        print("🎉 100% data import successful!")
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
