"""
COMPREHENSIVE HADEETHENC API IMPORTER
======================================
This script imports ALL data from HadeethEnc.com API including:
- Root categories and subcategories (with hierarchy)
- All hadiths with complete metadata
- ALL available language translations
- Proper database relationships maintained

Database Tables Used:
- books (HadeethEnc source book)
- chapters (category-based chapters)
- categories (root and subcategories)
- category_localizations (category translations)
- hadiths (main hadith records)
- hadith_translations (all language translations)
- hadith_category (many-to-many relationship)

Usage:
    python hadeethenc_complete_importer.py [options]

Options:
    --sample N          Import only first N hadiths per category (for testing)
    --categories-only   Import only categories/languages (skip hadiths)
    --resume           Resume from last checkpoint
    --verbose          Enable verbose logging
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import mysql.connector
from mysql.connector import Error as MySQLError
import time
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from config import DB_CONFIG

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "https://hadeethenc.com/api/v1"

# All supported languages from HadeethEnc API
LANGUAGES = [
    {"code": "ar", "name": "Arabic", "native": "عربي", "direction": "rtl"},
    {"code": "en", "name": "English", "native": "English", "direction": "ltr"},
    {"code": "fr", "name": "French", "native": "Français", "direction": "ltr"},
    {"code": "es", "name": "Spanish", "native": "Español", "direction": "ltr"},
    {"code": "tr", "name": "Turkish", "native": "Türkçe", "direction": "ltr"},
    {"code": "ur", "name": "Urdu", "native": "اردو", "direction": "rtl"},
    {"code": "id", "name": "Indonesian", "native": "Indonesia", "direction": "ltr"},
    {"code": "bs", "name": "Bosnian", "native": "Bosanski", "direction": "ltr"},
    {"code": "ru", "name": "Russian", "native": "Русский", "direction": "ltr"},
    {"code": "bn", "name": "Bengali", "native": "বাংলা", "direction": "ltr"},
    {"code": "zh", "name": "Chinese", "native": "中文", "direction": "ltr"},
    {"code": "fa", "name": "Persian", "native": "فارسی", "direction": "rtl"},
    {"code": "tl", "name": "Tagalog", "native": "Tagalog", "direction": "ltr"},
    {"code": "hi", "name": "Hindi", "native": "हिन्दी", "direction": "ltr"},
    {"code": "vi", "name": "Vietnamese", "native": "Tiếng Việt", "direction": "ltr"},
    {"code": "si", "name": "Sinhala", "native": "සිංහල", "direction": "ltr"},
    {"code": "ug", "name": "Uyghur", "native": "ئۇيغۇرچە", "direction": "rtl"},
    {"code": "ha", "name": "Hausa", "native": "Hausa", "direction": "ltr"},
    {"code": "ku", "name": "Kurdish", "native": "کوردی", "direction": "rtl"},
]

# API Rate limiting
REQUEST_DELAY = 0.1  # 100ms between requests
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

# Batch processing
BATCH_SIZE = 50
COMMIT_FREQUENCY = 100

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

class Logger:
    """Enhanced logging with timestamps and colors"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.start_time = time.time()
        
    def header(self, text):
        print(f"\n{'=' * 80}")
        print(f"🎯 {text}")
        print('=' * 80)
        
    def info(self, text):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ℹ️  {text}")
        
    def success(self, text):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ✅ {text}")
        
    def warning(self, text):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ⚠️  {text}")
        
    def error(self, text):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ❌ {text}")
        
    def debug(self, text):
        if self.verbose:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] 🔍 {text}")
            
    def progress(self, current, total, item_type="items"):
        percentage = (current / total * 100) if total > 0 else 0
        print(f"   Progress: {current}/{total} {item_type} ({percentage:.1f}%)")
        
    def elapsed_time(self):
        elapsed = time.time() - self.start_time
        return f"{elapsed / 60:.1f} minutes"


logger = Logger()


def fetch_api(endpoint: str, params: Dict = None, retry_count: int = 0) -> Optional[Dict]:
    """
    Fetch data from HadeethEnc API with retry logic
    
    Args:
        endpoint: API endpoint path
        params: Query parameters
        retry_count: Current retry attempt
        
    Returns:
        JSON response or None on failure
    """
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        time.sleep(REQUEST_DELAY)  # Rate limiting
        return response.json()
        
    except requests.exceptions.RequestException as e:
        if retry_count < RETRY_ATTEMPTS:
            logger.warning(f"Request failed, retrying... ({retry_count + 1}/{RETRY_ATTEMPTS})")
            time.sleep(RETRY_DELAY * (retry_count + 1))
            return fetch_api(endpoint, params, retry_count + 1)
        else:
            logger.error(f"Failed to fetch {endpoint}: {e}")
            return None


def get_db_connection():
    """Get MySQL database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        conn.autocommit = False  # Use transactions
        return conn
    except MySQLError as e:
        logger.error(f"Database connection failed: {e}")
        raise


def slugify(text: str) -> str:
    """Create URL-friendly slug from text"""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:500]  # Limit length


# ============================================================================
# DATABASE SETUP
# ============================================================================

def setup_hadeethenc_book(conn) -> int:
    """
    Create or get HadeethEnc source book and default chapter
    
    Returns:
        Tuple of (book_id, chapter_id)
    """
    logger.info("Setting up HadeethEnc book and chapter...")
    cursor = conn.cursor()
    
    try:
        # Create HadeethEnc book
        cursor.execute("""
            INSERT INTO books (name_en, name_ar, slug, created_at, updated_at)
            VALUES ('HadeethEnc Collection', 'موسوعة الحديث', 'hadeethenc', NOW(), NOW())
            ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
        """)
        book_id = cursor.lastrowid
        if book_id == 0:
            cursor.execute("SELECT id FROM books WHERE slug = 'hadeethenc'")
            book_id = cursor.fetchone()[0]
        
        # Create default chapter
        cursor.execute("""
            INSERT INTO chapters (book_id, chapter_number, created_at, updated_at)
            VALUES (%s, 1, NOW(), NOW())
            ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
        """, (book_id,))
        chapter_id = cursor.lastrowid
        if chapter_id == 0:
            cursor.execute("SELECT id FROM chapters WHERE book_id = %s LIMIT 1", (book_id,))
            chapter_id = cursor.fetchone()[0]
        
        conn.commit()
        logger.success(f"Book ID: {book_id}, Chapter ID: {chapter_id}")
        return book_id, chapter_id
        
    except MySQLError as e:
        conn.rollback()
        logger.error(f"Failed to setup book: {e}")
        raise
    finally:
        cursor.close()


# ============================================================================
# CATEGORY IMPORT
# ============================================================================

def import_categories(conn) -> Dict[int, Dict]:
    """
    Import all categories (roots and subcategories) with translations
    
    Returns:
        Dictionary mapping category_id to category info
    """
    logger.header("IMPORTING CATEGORIES")
    cursor = conn.cursor(dictionary=True)
    category_map = {}
    
    try:
        # Fetch root categories from API
        logger.info("Fetching root categories...")
        roots_data = fetch_api("categories/roots", {"language": "en"})
        
        if not roots_data:
            logger.error("Failed to fetch root categories")
            return category_map
            
        logger.info(f"Found {len(roots_data)} root categories")
        
        # Import each root category
        for cat_data in roots_data:
            cat_id = cat_data.get('id')
            title = cat_data.get('title', 'Untitled')
            parent_id = cat_data.get('parent_id')
            hadeeths_count = cat_data.get('hadeeths_count', 0)
            
            logger.debug(f"Importing category {cat_id}: {title}")
            
            # Insert category
            cursor.execute("""
                INSERT INTO categories (id, parent_id, name_en, name_ar, slug, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE 
                    name_en = VALUES(name_en),
                    parent_id = VALUES(parent_id),
                    updated_at = NOW()
            """, (cat_id, parent_id, title, title, slugify(title)))
            
            # Store in map
            category_map[cat_id] = {
                'title': title,
                'parent_id': parent_id,
                'hadeeths_count': hadeeths_count
            }
            
            # Import translations for this category
            import_category_translations(cursor, cat_id, title)
            
            # Fetch and import subcategories
            subcats = fetch_api("categories/list", {"language": "en", "category_id": cat_id})
            if subcats:
                for subcat in subcats:
                    sub_id = subcat.get('id')
                    sub_title = subcat.get('title', 'Untitled')
                    
                    cursor.execute("""
                        INSERT INTO categories (id, parent_id, name_en, name_ar, slug, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                        ON DUPLICATE KEY UPDATE 
                            name_en = VALUES(name_en),
                            parent_id = VALUES(parent_id),
                            updated_at = NOW()
                    """, (sub_id, cat_id, sub_title, sub_title, slugify(sub_title)))
                    
                    category_map[sub_id] = {
                        'title': sub_title,
                        'parent_id': cat_id,
                        'hadeeths_count': subcat.get('hadeeths_count', 0)
                    }
                    
                    import_category_translations(cursor, sub_id, sub_title)
        
        conn.commit()
        logger.success(f"Imported {len(category_map)} categories")
        
        return category_map
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Category import failed: {e}")
        raise
    finally:
        cursor.close()


def import_category_translations(cursor, category_id: int, default_title: str):
    """Import translations for a specific category"""
    
    for lang in LANGUAGES:
        try:
            # Fetch category in this language
            cat_data = fetch_api(f"categories/roots", {"language": lang['code']})
            
            if cat_data:
                # Find this category in the response
                cat_info = next((c for c in cat_data if str(c.get('id')) == str(category_id)), None)
                if cat_info:
                    title = cat_info.get('title', default_title)
                else:
                    title = default_title
            else:
                title = default_title
            
            # Insert translation
            cursor.execute("""
                INSERT INTO category_localizations 
                (category_id, localization_code, name, slug, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE 
                    name = VALUES(name),
                    slug = VALUES(slug),
                    updated_at = NOW()
            """, (category_id, lang['code'], title, slugify(title)))
            
        except Exception as e:
            logger.debug(f"Failed to import {lang['code']} translation for category {category_id}: {e}")


# ============================================================================
# HADITH IMPORT
# ============================================================================

def import_hadiths(conn, book_id: int, chapter_id: int, category_map: Dict, 
                   sample_limit: Optional[int] = None):
    """
    Import all hadiths with all language translations
    
    Args:
        conn: Database connection
        book_id: HadeethEnc book ID
        chapter_id: Default chapter ID
        category_map: Mapping of category IDs to info
        sample_limit: If set, import only N hadiths per category
    """
    logger.header("IMPORTING HADITHS WITH ALL TRANSLATIONS")
    
    cursor = conn.cursor(dictionary=True)
    stats = {
        'hadiths_imported': 0,
        'translations_imported': 0,
        'categories_processed': 0,
        'errors': 0
    }
    
    try:
        total_categories = len(category_map)
        
        for cat_id, cat_info in category_map.items():
            if sample_limit and stats['hadiths_imported'] >= sample_limit:
                logger.info(f"Sample limit reached ({sample_limit} hadiths)")
                break
                
            stats['categories_processed'] += 1
            logger.info(f"Processing category {cat_id}: {cat_info['title']} "
                       f"({stats['categories_processed']}/{total_categories})")
            
            # Fetch hadiths list for this category
            page = 1
            hadiths_in_category = 0
            
            while True:
                hadiths_data = fetch_api("hadeeths/list", {
                    "language": "en",
                    "category_id": cat_id,
                    "page": page,
                    "per_page": 20
                })
                
                if not hadiths_data or 'data' not in hadiths_data:
                    break
                
                hadiths_list = hadiths_data['data']
                if not hadiths_list:
                    break
                
                # Import each hadith
                for hadith_item in hadiths_list:
                    if sample_limit and stats['hadiths_imported'] >= sample_limit:
                        break
                        
                    hadith_id = hadith_item.get('id')
                    
                    if import_single_hadith(cursor, hadith_id, book_id, chapter_id, cat_id):
                        stats['hadiths_imported'] += 1
                        hadiths_in_category += 1
                        
                        # Import all translations
                        trans_count = import_hadith_translations(cursor, hadith_id)
                        stats['translations_imported'] += trans_count
                    else:
                        stats['errors'] += 1
                    
                    # Commit periodically
                    if stats['hadiths_imported'] % COMMIT_FREQUENCY == 0:
                        conn.commit()
                        logger.progress(stats['hadiths_imported'], 
                                      sample_limit or "ALL", "hadiths")
                
                # Check if there are more pages
                meta = hadiths_data.get('meta', {})
                if page >= int(meta.get('last_page', 1)):
                    break
                    
                page += 1
            
            logger.debug(f"Imported {hadiths_in_category} hadiths from category {cat_id}")
        
        conn.commit()
        
        # Print statistics
        logger.success(f"Hadith import completed!")
        logger.info(f"  Hadiths imported: {stats['hadiths_imported']}")
        logger.info(f"  Translations imported: {stats['translations_imported']}")
        logger.info(f"  Average translations per hadith: "
                   f"{stats['translations_imported'] / stats['hadiths_imported']:.1f}" 
                   if stats['hadiths_imported'] > 0 else "N/A")
        logger.info(f"  Errors: {stats['errors']}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Hadith import failed: {e}")
        raise
    finally:
        cursor.close()


def import_single_hadith(cursor, hadith_id: str, book_id: int, 
                        chapter_id: int, category_id: int) -> bool:
    """
    Import a single hadith record (Arabic)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Fetch hadith details in Arabic
        hadith_data = fetch_api("hadeeths/one", {
            "id": hadith_id,
            "language": "ar"
        })
        
        if not hadith_data:
            logger.warning(f"Could not fetch hadith {hadith_id}")
            return False
        
        # Extract fields
        title = hadith_data.get('title', '')[:255]
        arabic_text = hadith_data.get('hadeeth', '')
        grade = hadith_data.get('grade', '')[:100]
        attribution = hadith_data.get('attribution', '')[:255] if hadith_data.get('attribution') else None
        
        # Insert hadith
        cursor.execute("""
            INSERT INTO hadiths 
            (id, book_id, chapter_id, hadith_number, arabic_text, grade, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                arabic_text = VALUES(arabic_text),
                grade = VALUES(grade),
                updated_at = NOW()
        """, (hadith_id, book_id, chapter_id, hadith_id, arabic_text, grade))
        
        # Link to category
        cursor.execute("""
            INSERT IGNORE INTO hadith_category (hadith_id, category_id)
            VALUES (%s, %s)
        """, (hadith_id, category_id))
        
        return True
        
    except Exception as e:
        logger.debug(f"Error importing hadith {hadith_id}: {e}")
        return False


def import_hadith_translations(cursor, hadith_id: str) -> int:
    """
    Import all language translations for a hadith
    
    Returns:
        Number of translations imported
    """
    translations_imported = 0
    
    for lang in LANGUAGES:
        try:
            # Fetch hadith in this language
            hadith_data = fetch_api("hadeeths/one", {
                "id": hadith_id,
                "language": lang['code']
            })
            
            if not hadith_data:
                continue
            
            # Extract translation fields
            translation_text = hadith_data.get('hadeeth', '')
            if not translation_text:
                continue  # Skip if no translation text
            
            explanation = hadith_data.get('explanation', '')
            hints = hadith_data.get('hints', [])
            hints_text = '\n'.join(hints) if isinstance(hints, list) else str(hints)
            
            # Get localization_id (use language code numeric representation)
            localization_id = next((i for i, l in enumerate(LANGUAGES, 1) 
                                  if l['code'] == lang['code']), 0)
            
            # Insert translation
            cursor.execute("""
                INSERT INTO hadith_translations
                (hadith_id, localization_id, localization_code, translation_text, 
                 created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    translation_text = VALUES(translation_text),
                    updated_at = NOW()
            """, (hadith_id, localization_id, lang['code'], translation_text))
            
            translations_imported += 1
            
        except Exception as e:
            logger.debug(f"Error importing {lang['code']} translation for hadith {hadith_id}: {e}")
    
    return translations_imported


# ============================================================================
# VERIFICATION
# ============================================================================

def verify_import(conn):
    """Verify the import was successful"""
    logger.header("VERIFICATION REPORT")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Categories
        cursor.execute("SELECT COUNT(*) as count FROM categories")
        cat_count = cursor.fetchone()['count']
        logger.info(f"✅ Categories: {cat_count}")
        
        cursor.execute("SELECT COUNT(*) as count FROM category_localizations")
        cat_loc_count = cursor.fetchone()['count']
        logger.info(f"✅ Category localizations: {cat_loc_count}")
        
        # Hadiths
        cursor.execute("SELECT COUNT(*) as count FROM hadiths")
        hadith_count = cursor.fetchone()['count']
        logger.info(f"✅ Hadiths: {hadith_count}")
        
        cursor.execute("SELECT COUNT(*) as count FROM hadith_translations")
        trans_count = cursor.fetchone()['count']
        logger.info(f"✅ Hadith translations: {trans_count}")
        
        if hadith_count > 0:
            avg_trans = trans_count / hadith_count
            logger.info(f"✅ Average translations per hadith: {avg_trans:.1f}")
        
        # Language coverage
        logger.info("\n📊 Translation Coverage by Language:")
        cursor.execute("""
            SELECT localization_code, COUNT(*) as count
            FROM hadith_translations
            GROUP BY localization_code
            ORDER BY count DESC
        """)
        
        for row in cursor.fetchall():
            lang_code = row['localization_code']
            count = row['count']
            lang_name = next((l['name'] for l in LANGUAGES if l['code'] == lang_code), lang_code)
            coverage = (count / hadith_count * 100) if hadith_count > 0 else 0
            logger.info(f"   {lang_code} ({lang_name}): {count} ({coverage:.1f}%)")
        
        # Category-Hadith relationships
        cursor.execute("SELECT COUNT(*) as count FROM hadith_category")
        rel_count = cursor.fetchone()['count']
        logger.info(f"\n✅ Hadith-Category relationships: {rel_count}")
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
    finally:
        cursor.close()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Import complete HadeethEnc data with all translations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--sample', type=int, metavar='N',
                       help='Import only first N hadiths (for testing)')
    parser.add_argument('--categories-only', action='store_true',
                       help='Import only categories and skip hadiths')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose debug logging')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    # Set verbose mode
    if args.verbose:
        logger.verbose = True
    
    # Display header
    logger.header("HADEETHENC COMPLETE DATA IMPORTER")
    logger.info("This script will import:")
    logger.info("  ✓ All category hierarchies (7+ root categories)")
    logger.info("  ✓ All subcategories")
    logger.info("  ✓ All hadiths (~3000+ hadiths)")
    logger.info(f"  ✓ All language translations ({len(LANGUAGES)} languages)")
    logger.info("  ✓ Proper database relationships")
    
    if args.sample:
        logger.warning(f"SAMPLE MODE: Only {args.sample} hadiths will be imported")
    
    if args.categories_only:
        logger.warning("CATEGORIES ONLY: Hadiths will be skipped")
    
    logger.info(f"\nEstimated time: {'5-10 minutes' if args.sample else '2-4 hours'}")
    
    # Confirm execution
    if not args.yes:
        response = input("\nDo you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            logger.info("Import cancelled by user")
            return
    
    # Start import
    start_time = time.time()
    conn = None
    
    try:
        # Connect to database
        logger.info("\nConnecting to database...")
        conn = get_db_connection()
        logger.success("Database connected")
        
        # Step 1: Setup HadeethEnc book/chapter
        book_id, chapter_id = setup_hadeethenc_book(conn)
        
        # Step 2: Import categories
        category_map = import_categories(conn)
        
        # Step 3: Import hadiths (unless categories-only)
        if not args.categories_only:
            import_hadiths(conn, book_id, chapter_id, category_map, args.sample)
        else:
            logger.info("Skipping hadith import (--categories-only)")
        
        # Step 4: Verify
        verify_import(conn)
        
        # Success
        elapsed = time.time() - start_time
        logger.header("IMPORT COMPLETED SUCCESSFULLY")
        logger.success(f"Total time: {elapsed / 60:.1f} minutes")
        logger.success("All data imported with proper relationships")
        logger.info("\nYou can now use the API endpoints to access the data")
        
    except KeyboardInterrupt:
        logger.warning("\nImport cancelled by user (Ctrl+C)")
        if conn:
            conn.rollback()
        return 1
        
    except Exception as e:
        logger.error(f"\nImport failed with error: {e}")
        if conn:
            conn.rollback()
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")
    
    return 0


if __name__ == "__main__":
    exit(main())
