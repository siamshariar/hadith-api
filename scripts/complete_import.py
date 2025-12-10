"""
COMPLETE IMPORT SCRIPT - Imports from ALL sources and ensures 100% API coverage
1. Fawaz Hadith API (Arabic + translations)
2. HadeethEnc (Categories + detailed hadiths)
3. Your own API (if any additional data)
"""

import sys
import os
import time
import mysql.connector
import requests
import json
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal

# Database configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '123456',
    'database': 'hadith_api_prod',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

# API endpoints - COMPLETE LIST
API_ENDPOINTS = {
    # FAWAZ API endpoints
    'fawaz': {
        'base': 'https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1',
        'editions': 'https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions.json',
        'edition_info': 'https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/info/editions.json',
        'book_info': 'https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/info/books.json',
        'hadith_pattern': 'https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/{edition}/{number}.json',
        'min_pattern': 'https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/{edition}/{number}.min.json'
    },
    
    # HADEETHENC API endpoints
    'hadeethenc': {
        'base': 'https://hadeethenc.com/api/v1',
        'categories': 'https://hadeethenc.com/api/v1/categories/list/?language=en',
        'hadiths_by_category': 'https://hadeethenc.com/api/v1/hadeeths/list/?language=en&category_id={category_id}&page={page}&per_page={per_page}',
        'hadith_detail': 'https://hadeethenc.com/api/v1/hadeeths/one/?language={language}&id={hadith_id}',
        'search': 'https://hadeethenc.com/api/v1/hadeeths/search/?language=en&q={query}&page={page}&per_page={per_page}',
        'random': 'https://hadeethenc.com/api/v1/hadeeths/random/'
    }
}

# Supported languages and their codes
LANGUAGES = {
    'ar': {'id': 1, 'name': 'Arabic', 'direction': 'rtl'},
    'en': {'id': 2, 'name': 'English', 'direction': 'ltr'},
    'ur': {'id': 3, 'name': 'Urdu', 'direction': 'rtl'},
    'bn': {'id': 4, 'name': 'Bengali', 'direction': 'ltr'},
    'tr': {'id': 5, 'name': 'Turkish', 'direction': 'ltr'},
    'fa': {'id': 6, 'name': 'Persian', 'direction': 'rtl'},
    'fr': {'id': 7, 'name': 'French', 'direction': 'ltr'},
    'es': {'id': 8, 'name': 'Spanish', 'direction': 'ltr'},
    'ru': {'id': 9, 'name': 'Russian', 'direction': 'ltr'},
    'id': {'id': 10, 'name': 'Indonesian', 'direction': 'ltr'},
    'ms': {'id': 11, 'name': 'Malay', 'direction': 'ltr'},
    'bs': {'id': 12, 'name': 'Bosnian', 'direction': 'ltr'},
    'zh': {'id': 13, 'name': 'Chinese', 'direction': 'ltr'},
    'tl': {'id': 14, 'name': 'Tagalog', 'direction': 'ltr'},
    'hi': {'id': 15, 'name': 'Hindi', 'direction': 'ltr'},
    'vi': {'id': 16, 'name': 'Vietnamese', 'direction': 'ltr'},
    'si': {'id': 17, 'name': 'Sinhala', 'direction': 'ltr'},
    'ug': {'id': 18, 'name': 'Uyghur', 'direction': 'rtl'},
    'ha': {'id': 19, 'name': 'Hausa', 'direction': 'ltr'},
    'ku': {'id': 20, 'name': 'Kurdish', 'direction': 'rtl'}
}

# Book mapping - Fawaz API to HadeethEnc
BOOK_MAPPING = {
    'bukhari': {'fawaz': 'ara-bukhari', 'hadeethenc': None, 'name_en': 'Sahih al-Bukhari'},
    'muslim': {'fawaz': 'ara-muslim', 'hadeethenc': None, 'name_en': 'Sahih Muslim'},
    'abudawud': {'fawaz': 'ara-abudawud', 'hadeethenc': None, 'name_en': 'Sunan Abu Dawud'},
    'tirmidhi': {'fawaz': 'ara-tirmidhi', 'hadeethenc': None, 'name_en': 'Jami al-Tirmidhi'},
    'nasai': {'fawaz': 'ara-nasai', 'hadeethenc': None, 'name_en': 'Sunan al-Nasa\'i'},
    'ibnmajah': {'fawaz': 'ara-ibnmajah', 'hadeethenc': None, 'name_en': 'Sunan Ibn Majah'},
    'malik': {'fawaz': 'ara-malik', 'hadeethenc': None, 'name_en': 'Muwatta Malik'},
    'hadeethenc': {'fawaz': None, 'hadeethenc': True, 'name_en': 'HadeethEnc Collection'}
}

def log(message: str, level: str = "INFO"):
    """Log messages with timestamp and level"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def get_db_connection():
    """Get database connection"""
    return mysql.connector.connect(**DB_CONFIG)

def fetch_json(url: str, timeout: int = 30) -> Optional[dict]:
    """Fetch JSON from URL with error handling"""
    try:
        log(f"Fetching: {url}", "DEBUG")
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"Failed to fetch {url}: {e}", "WARNING")
        return None
    except json.JSONDecodeError as e:
        log(f"Invalid JSON from {url}: {e}", "WARNING")
        return None

def show_api_endpoints():
    """Display all API endpoints"""
    print("\n" + "="*80)
    print("AVAILABLE API ENDPOINTS")
    print("="*80)
    
    for api_name, endpoints in API_ENDPOINTS.items():
        print(f"\n{api_name.upper()} API:")
        print("-" * 40)
        for key, value in endpoints.items():
            print(f"  {key}: {value}")
    
    print("\n" + "="*80)
    print("BOOK MAPPING")
    print("="*80)
    for book_code, info in BOOK_MAPPING.items():
        print(f"{book_code}: {info['name_en']}")
        if info['fawaz']:
            print(f"  Fawaz API code: {info['fawaz']}")
        if info['hadeethenc']:
            print(f"  HadeethEnc: Yes")
    
    print("\n" + "="*80)
    print("SUPPORTED LANGUAGES")
    print("="*80)
    for lang_code, info in LANGUAGES.items():
        print(f"{lang_code}: {info['name']} ({info['direction']})")

# ==================== STEP 1: ENSURE DATABASE STRUCTURE ====================

def ensure_database_structure():
    """Create necessary tables if they don't exist"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Disable foreign key checks temporarily
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    
    # 1. Books table (no dependencies)
    log("Creating books table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INT PRIMARY KEY AUTO_INCREMENT,
            code VARCHAR(50) UNIQUE NOT NULL,
            name_en VARCHAR(255) NOT NULL,
            name_ar VARCHAR(255),
            total_hadith INT DEFAULT 0,
            source VARCHAR(50) NOT NULL DEFAULT 'fawaz',
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_code (code),
            INDEX idx_source (source)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 2. Categories table with self-referencing foreign key in CREATE TABLE
    log("Creating categories table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INT PRIMARY KEY AUTO_INCREMENT,
            parent_id INT DEFAULT NULL,
            name_en VARCHAR(255) NOT NULL,
            name_ar VARCHAR(255),
            total_hadith INT DEFAULT 0,
            slug VARCHAR(255) UNIQUE,
            source VARCHAR(50) NOT NULL DEFAULT 'hadeethenc',
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_parent_id (parent_id),
            INDEX idx_slug (slug),
            INDEX idx_source (source),
            CONSTRAINT fk_categories_parent FOREIGN KEY (parent_id) 
                REFERENCES categories(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 3. Chapters table (depends on books)
    log("Creating chapters table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chapters (
            id INT PRIMARY KEY AUTO_INCREMENT,
            book_id INT NOT NULL,
            chapter_no INT NOT NULL,
            name_en VARCHAR(255) NOT NULL,
            name_ar VARCHAR(255),
            total_hadith INT DEFAULT 0,
            source VARCHAR(50) NOT NULL DEFAULT 'fawaz',
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_book_chapter (book_id, chapter_no),
            INDEX idx_book_id (book_id),
            INDEX idx_source (source),
            CONSTRAINT fk_chapters_books FOREIGN KEY (book_id) 
                REFERENCES books(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 4. Main hadiths table (depends on books and chapters)
    log("Creating hadiths table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hadiths (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            book_id INT NOT NULL,
            chapter_id INT NOT NULL,
            hadith_number VARCHAR(50) NOT NULL,
            arabic_text LONGTEXT NOT NULL,
            grade VARCHAR(100),
            explanation LONGTEXT,
            hints LONGTEXT,
            word_meanings LONGTEXT,
            `references` LONGTEXT,
            narrator VARCHAR(500),
            source VARCHAR(50) NOT NULL DEFAULT 'fawaz',
            external_id VARCHAR(100),
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_book_chapter (book_id, chapter_id),
            INDEX idx_hadith_number (hadith_number),
            INDEX idx_source (source),
            INDEX idx_external_id (external_id),
            FULLTEXT idx_arabic_text (arabic_text),
            CONSTRAINT fk_hadiths_books FOREIGN KEY (book_id) 
                REFERENCES books(id) ON DELETE CASCADE,
            CONSTRAINT fk_hadiths_chapters FOREIGN KEY (chapter_id) 
                REFERENCES chapters(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 5. Translations table (depends on hadiths)
    log("Creating translations table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hadith_translations (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            hadith_id BIGINT NOT NULL,
            language_code VARCHAR(10) NOT NULL,
            translation_text LONGTEXT NOT NULL,
            explanation LONGTEXT,
            hints LONGTEXT,
            `references` LONGTEXT,
            narrator VARCHAR(500),
            source VARCHAR(50) NOT NULL DEFAULT 'fawaz',
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_hadith_language (hadith_id, language_code),
            INDEX idx_language (language_code),
            INDEX idx_source (source),
            FULLTEXT idx_translation_text (translation_text),
            CONSTRAINT fk_translations_hadiths FOREIGN KEY (hadith_id) 
                REFERENCES hadiths(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 6. Hadith-Category mapping (depends on hadiths and categories)
    log("Creating hadith_category mapping table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hadith_category (
            hadith_id BIGINT NOT NULL,
            category_id INT NOT NULL,
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (hadith_id, category_id),
            INDEX idx_category_id (category_id),
            INDEX idx_hadith_id (hadith_id),
            CONSTRAINT fk_hadith_category_hadiths FOREIGN KEY (hadith_id) 
                REFERENCES hadiths(id) ON DELETE CASCADE,
            CONSTRAINT fk_hadith_category_categories FOREIGN KEY (category_id) 
                REFERENCES categories(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 7. Reference translations table (optional, for better organization)
    log("Creating reference translations table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hadith_reference_translations (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            hadith_id BIGINT NOT NULL,
            language_code VARCHAR(10) NOT NULL,
            `references` LONGTEXT,
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY idx_hadith_lang (hadith_id, language_code),
            INDEX idx_hadith_id (hadith_id),
            INDEX idx_language_code (language_code),
            CONSTRAINT fk_ref_translations_hadiths FOREIGN KEY (hadith_id) 
                REFERENCES hadiths(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # Re-enable foreign key checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log("Database structure ensured successfully", "SUCCESS")
    return True

# ==================== STEP 2: IMPORT FROM FAWAZ API ====================

def check_missing_fawaz_data(book_code: str, max_hadiths: int = 500) -> Tuple[int, List[int]]:
    """Check which hadiths are missing for a book"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get book info
    cursor.execute("SELECT id FROM books WHERE code = %s", (book_code,))
    result = cursor.fetchone()
    
    if not result:
        log(f"Book {book_code} not found in database", "WARNING")
        cursor.close()
        conn.close()
        return 0, []
    
    book_id = result[0]
    
    # Get existing hadith numbers
    cursor.execute("""
        SELECT hadith_number 
        FROM hadiths 
        WHERE book_id = %s 
        ORDER BY CAST(hadith_number AS UNSIGNED)
    """, (book_id,))
    
    existing_numbers = [int(row[0]) for row in cursor.fetchall() if row[0].isdigit()]
    
    cursor.close()
    conn.close()
    
    # Find missing numbers
    all_numbers = list(range(1, max_hadiths + 1))
    missing_numbers = [num for num in all_numbers if num not in existing_numbers]
    
    log(f"Book {book_code}: {len(existing_numbers)} existing, {len(missing_numbers)} missing hadiths", "INFO")
    
    return len(existing_numbers), missing_numbers

def import_fawaz_hadiths(book_code: str, max_hadiths: int = 500, incremental: bool = True):
    """Import hadiths from Fawaz API for a specific book"""
    
    if book_code not in BOOK_MAPPING:
        log(f"Book {book_code} not in mapping", "ERROR")
        return False
    
    book_info = BOOK_MAPPING[book_code]
    fawaz_code = book_info['fawaz']
    
    if not fawaz_code:
        log(f"No Fawaz code for {book_code}", "WARNING")
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get or create book
    cursor.execute("SELECT id FROM books WHERE code = %s", (book_code,))
    result = cursor.fetchone()
    
    if result:
        book_id = result[0]
    else:
        cursor.execute("""
            INSERT INTO books (code, name_en, source)
            VALUES (%s, %s, 'fawaz')
        """, (book_code, book_info['name_en']))
        book_id = cursor.lastrowid
        conn.commit()
    
    # Check for missing data if incremental mode
    hadith_numbers_to_import = list(range(1, max_hadiths + 1))
    if incremental:
        _, existing_numbers = check_missing_fawaz_data(book_code, max_hadiths)
        # If we found existing numbers, import only missing ones
        if existing_numbers:
            hadith_numbers_to_import = existing_numbers
            log(f"Incremental import: importing {len(hadith_numbers_to_import)} missing hadiths for {book_code}", "INFO")
        else:
            log(f"Full import: importing all {len(hadith_numbers_to_import)} hadiths for {book_code}", "INFO")
    else:
        log(f"Forced full import: importing all {len(hadith_numbers_to_import)} hadiths for {book_code}", "INFO")
    
    imported_count = 0
    translation_count = 0
    
    # Get available languages for this book from Fawaz
    fawaz_languages = get_fawaz_languages_for_book(fawaz_code)
    log(f"Available languages for {book_code}: {fawaz_languages}", "INFO")
    
    for hadith_num in hadith_numbers_to_import:
        # Try to get hadith data
        hadith_data = None
        urls = [
            API_ENDPOINTS['fawaz']['hadith_pattern'].format(edition=fawaz_code, number=hadith_num),
            API_ENDPOINTS['fawaz']['min_pattern'].format(edition=fawaz_code, number=hadith_num)
        ]
        
        for url in urls:
            hadith_data = fetch_json(url)
            if hadith_data:
                break
        
        if not hadith_data:
            # Try 3 more consecutive hadiths before giving up
            failures = 0
            for i in range(1, 4):
                next_num = hadith_num + i
                if next_num > max_hadiths:
                    break
                
                test_url = API_ENDPOINTS['fawaz']['hadith_pattern'].format(edition=fawaz_code, number=next_num)
                test_data = fetch_json(test_url)
                if not test_data:
                    failures += 1
            
            if failures >= 3:
                log(f"Reached end of hadiths for {book_code} at number {hadith_num}", "INFO")
                break
            continue
        
        # Process hadith data
        try:
            # Extract Arabic text
            arabic_text = ""
            metadata = hadith_data.get('metadata', {})
            hadiths_list = hadith_data.get('hadiths', [])
            
            if hadiths_list:
                hadith_item = hadiths_list[0]
                arabic_text = hadith_item.get('text', '')
                
                if not arabic_text or len(arabic_text.strip()) < 10:
                    continue
                
                # Get chapter information
                chapter_no = hadith_item.get('chapter', 1)
                if isinstance(chapter_no, str):
                    try:
                        chapter_no = int(chapter_no)
                    except:
                        chapter_no = 1
                
                # Get grade
                grades = hadith_item.get('grades', [])
                grade_text = None
                if grades and isinstance(grades, list):
                    grade_list = []
                    for grade in grades:
                        if isinstance(grade, dict):
                            grade_list.append(grade.get('grade', grade.get('name', '')))
                        else:
                            grade_list.append(str(grade))
                    grade_text = ' | '.join([g for g in grade_list if g])
                
                # Check if hadith already exists
                cursor.execute("""
                    SELECT id FROM hadiths 
                    WHERE book_id = %s AND arabic_text = %s
                    LIMIT 1
                """, (book_id, arabic_text))
                
                existing = cursor.fetchone()
                
                if existing:
                    hadith_id = existing[0]
                    # Update last_imported_at timestamp
                    cursor.execute("""
                        UPDATE hadiths 
                        SET last_imported_at = NOW() 
                        WHERE id = %s
                    """, (hadith_id,))
                else:
                    # Get or create chapter
                    cursor.execute("""
                        SELECT id FROM chapters 
                        WHERE book_id = %s AND chapter_no = %s
                        LIMIT 1
                    """, (book_id, chapter_no))
                    
                    chapter_result = cursor.fetchone()
                    
                    if chapter_result:
                        chapter_id = chapter_result[0]
                        # Update last_imported_at timestamp
                        cursor.execute("""
                            UPDATE chapters 
                            SET last_imported_at = NOW() 
                            WHERE id = %s
                        """, (chapter_id,))
                    else:
                        # Create chapter with generic name
                        chapter_name = metadata.get('section', {}).get(str(chapter_no), f'Chapter {chapter_no}')
                        cursor.execute("""
                            INSERT INTO chapters (book_id, chapter_no, name_en, source, last_imported_at)
                            VALUES (%s, %s, %s, 'fawaz', NOW())
                        """, (book_id, chapter_no, chapter_name))
                        chapter_id = cursor.lastrowid
                    
                    # Insert hadith
                    cursor.execute("""
                        INSERT INTO hadiths (
                            book_id, chapter_id, hadith_number, arabic_text, grade,
                            source, external_id, last_imported_at
                        ) VALUES (%s, %s, %s, %s, %s, 'fawaz', %s, NOW())
                    """, (book_id, chapter_id, str(hadith_num), arabic_text, grade_text, str(hadith_num)))
                    
                    hadith_id = cursor.lastrowid
                    imported_count += 1
                
                # Import translations for other languages
                for lang_code in fawaz_languages:
                    if lang_code == 'ar':  # Already have Arabic
                        continue
                    
                    # Check if translation already exists
                    cursor.execute("""
                        SELECT id FROM hadith_translations 
                        WHERE hadith_id = %s AND language_code = %s
                        LIMIT 1
                    """, (hadith_id, lang_code))
                    
                    if cursor.fetchone():
                        # Update last_imported_at timestamp
                        cursor.execute("""
                            UPDATE hadith_translations 
                            SET last_imported_at = NOW() 
                            WHERE hadith_id = %s AND language_code = %s
                        """, (hadith_id, lang_code))
                        continue
                    
                    # Try to get translation
                    trans_code = fawaz_code.replace('ara-', f'{lang_code[:3]}-') if lang_code != 'en' else fawaz_code.replace('ara-', 'eng-')
                    trans_url = API_ENDPOINTS['fawaz']['hadith_pattern'].format(edition=trans_code, number=hadith_num)
                    trans_data = fetch_json(trans_url)
                    
                    if trans_data and trans_data.get('hadiths'):
                        trans_item = trans_data['hadiths'][0]
                        trans_text = trans_item.get('text', '')
                        
                        if trans_text and len(trans_text.strip()) > 10:
                            cursor.execute("""
                                INSERT INTO hadith_translations (
                                    hadith_id, language_code, translation_text, source, last_imported_at
                                ) VALUES (%s, %s, %s, 'fawaz', NOW())
                            """, (hadith_id, lang_code, trans_text))
                            translation_count += 1
                
                conn.commit()
                
                if imported_count % 50 == 0:
                    log(f"Imported {imported_count} hadiths, {translation_count} translations for {book_code}", "INFO")
                    
        except Exception as e:
            log(f"Error processing hadith {hadith_num} for {book_code}: {e}", "ERROR")
            conn.rollback()
            continue
    
    # Update book stats and timestamp
    cursor.execute("""
        UPDATE books 
        SET total_hadith = (SELECT COUNT(*) FROM hadiths WHERE book_id = %s),
            last_imported_at = NOW(),
            updated_at = NOW()
        WHERE id = %s
    """, (book_id, book_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log(f"Finished importing {book_code}: {imported_count} hadiths, {translation_count} translations", "SUCCESS")
    return True

def get_fawaz_languages_for_book(fawaz_code: str) -> List[str]:
    """Get available languages for a book from Fawaz API"""
    # Get editions list to see available translations
    editions_url = API_ENDPOINTS['fawaz']['editions']
    editions_data = fetch_json(editions_url)
    
    if not editions_data:
        return ['ar', 'en']  # Default to Arabic and English
    
    available_langs = ['ar']  # Always include Arabic
    
    # Handle different response formats
    # The API might return a list of strings or a list of dictionaries
    if isinstance(editions_data, list):
        editions_list = editions_data
    elif isinstance(editions_data, dict):
        # If it's a dict, try to get the list from it
        editions_list = editions_data.get('editions', editions_data.get('data', []))
    else:
        editions_list = []
    
    # Check for English
    eng_code = fawaz_code.replace('ara-', 'eng-')
    for edition in editions_list:
        if isinstance(edition, dict):
            edition_name = edition.get('name', '')
        else:
            edition_name = str(edition)
        
        if eng_code in edition_name.lower():
            available_langs.append('en')
            break
    
    # Check for other common languages
    lang_prefixes = {
        'ur': 'urd-', 'bn': 'ben-', 'tr': 'tur-', 
        'fr': 'fre-', 'es': 'spa-', 'ru': 'rus-',
        'hi': 'hin-', 'id': 'ind-', 'fa': 'fas-',
        'ms': 'msa-', 'bs': 'bos-', 'zh': 'zho-'
    }
    
    for lang, prefix in lang_prefixes.items():
        lang_code = fawaz_code.replace('ara-', prefix)
        for edition in editions_list:
            if isinstance(edition, dict):
                edition_name = edition.get('name', '')
            else:
                edition_name = str(edition)
            
            if lang_code in edition_name.lower():
                available_langs.append(lang)
                break
    
    # Remove duplicates
    available_langs = list(dict.fromkeys(available_langs))
    
    log(f"Found languages for {fawaz_code}: {available_langs}", "DEBUG")
    return available_langs

# ==================== STEP 3: IMPORT FROM HADEETHENC ====================

def check_missing_hadeethenc_data(category_limit: int = 5) -> Tuple[int, List[int]]:
    """Check which categories have missing data"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get categories that need updating (no last_imported_at or old)
    cursor.execute("""
        SELECT c.id, c.name_en, c.total_hadith
        FROM categories c
        WHERE c.source = 'hadeethenc'
        AND (c.last_imported_at IS NULL OR c.last_imported_at < DATE_SUB(NOW(), INTERVAL 7 DAY))
        ORDER BY c.id
        LIMIT %s
    """, (category_limit,))
    
    categories_to_update = []
    for row in cursor.fetchall():
        categories_to_update.append({
            'id': row[0],
            'name': row[1],
            'total_hadith': row[2]
        })
    
    cursor.close()
    conn.close()
    
    log(f"Found {len(categories_to_update)} categories needing update", "INFO")
    return len(categories_to_update), categories_to_update

def import_hadeethenc_categories(incremental: bool = True, category_limit: int = 5):
    """Import all categories from HadeethEnc"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get or create HadeethEnc book
    cursor.execute("SELECT id FROM books WHERE code = 'hadeethenc'")
    result = cursor.fetchone()
    
    if result:
        book_id = result[0]
    else:
        cursor.execute("""
            INSERT INTO books (code, name_en, source)
            VALUES ('hadeethenc', 'HadeethEnc Collection', 'hadeethenc')
        """)
        book_id = cursor.lastrowid
        
        # Create a single chapter for HadeethEnc
        cursor.execute("""
            INSERT INTO chapters (book_id, chapter_no, name_en, source)
            VALUES (%s, 1, 'All Hadiths', 'hadeethenc')
        """, (book_id,))
        conn.commit()
    
    # Fetch categories from HadeethEnc
    categories_url = API_ENDPOINTS['hadeethenc']['categories']
    categories_data = fetch_json(categories_url)
    
    if not categories_data:
        log("Failed to fetch categories from HadeethEnc", "ERROR")
        return False
    
    log(f"Found {len(categories_data)} categories", "INFO")
    
    # First pass: insert all categories
    for category in categories_data:
        try:
            cat_id = int(category['id'])
            cat_name = category['title']
            parent_id = category.get('parent_id')
            hadiths_count = int(category.get('hadeeths_count', 0))
            
            # Create slug
            slug = cat_name.lower().replace(' ', '-').replace('/', '-').replace('(', '').replace(')', '').replace(',', '').replace(':', '')
            
            # Check if category exists
            cursor.execute("SELECT id, last_imported_at FROM categories WHERE id = %s", (cat_id,))
            cat_result = cursor.fetchone()
            
            if cat_result:
                # Update existing
                cursor.execute("""
                    UPDATE categories 
                    SET name_en = %s, parent_id = %s, total_hadith = %s, slug = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (cat_name, parent_id, hadiths_count, slug, cat_id))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO categories (id, parent_id, name_en, total_hadith, slug, source)
                    VALUES (%s, %s, %s, %s, %s, 'hadeethenc')
                """, (cat_id, parent_id, cat_name, hadiths_count, slug))
        except Exception as e:
            log(f"Error processing category {category.get('id')}: {e}", "ERROR")
            continue
    
    conn.commit()
    log("Categories inserted/updated", "INFO")
    
    # Determine which categories to process
    if incremental:
        # Get categories that need updating
        _, categories_to_process = check_missing_hadeethenc_data(category_limit)
        log(f"Incremental import: processing {len(categories_to_process)} categories", "INFO")
    else:
        # Process first N categories
        categories_to_process = []
        for category in categories_data[:category_limit]:
            if int(category.get('hadeeths_count', 0)) > 0:
                categories_to_process.append({
                    'id': int(category['id']),
                    'name': category['title'],
                    'total_hadith': int(category.get('hadeeths_count', 0))
                })
        log(f"Full import: processing {len(categories_to_process)} categories", "INFO")
    
    # Now import hadiths for each category
    total_imported = 0
    
    for cat_info in categories_to_process:
        try:
            cat_id = cat_info['id']
            cat_name = cat_info['name']
            hadiths_count = cat_info['total_hadith']
            
            log(f"Importing hadiths for category: {cat_name} ({hadiths_count} hadiths)", "INFO")
            
            page = 1
            imported_in_category = 0
            
            while True:
                hadiths_url = API_ENDPOINTS['hadeethenc']['hadiths_by_category'].format(
                    category_id=cat_id, 
                    page=page, 
                    per_page=20
                )
                hadiths_data = fetch_json(hadiths_url)
                
                if not hadiths_data or not hadiths_data.get('data'):
                    break
                
                hadith_list = hadiths_data['data']
                
                for hadith_item in hadith_list:
                    try:
                        hadith_id_api = hadith_item['id']
                        
                        # Get detailed hadith data in Arabic
                        detail_url = API_ENDPOINTS['hadeethenc']['hadith_detail'].format(
                            language='ar', 
                            hadith_id=hadith_id_api
                        )
                        detail_data = fetch_json(detail_url)
                        
                        if not detail_data:
                            continue
                        
                        # Extract data
                        arabic_text = detail_data.get('hadeeth', '')
                        if not arabic_text or len(arabic_text.strip()) < 10:
                            continue
                        
                        grade = detail_data.get('grade', '')
                        explanation = detail_data.get('explanation', '')
                        
                        # Process hints
                        hints = detail_data.get('hints', [])
                        if hints and isinstance(hints, list):
                            hints_text = '\n'.join([f"- {hint}" for hint in hints if hint])
                        else:
                            hints_text = None
                        
                        # Process word meanings
                        word_meanings = detail_data.get('words_meanings', [])
                        if word_meanings and isinstance(word_meanings, list):
                            meanings_text = '\n'.join([f"- {meaning}" for meaning in word_meanings if meaning])
                        else:
                            meanings_text = None
                        
                        # Process references
                        references = detail_data.get('references', [])
                        if references and isinstance(references, list):
                            refs_text = '\n'.join([f"- {ref}" for ref in references if ref])
                        else:
                            refs_text = detail_data.get('attribution', '')
                        
                        # Check if hadith already exists by Arabic text
                        cursor.execute("""
                            SELECT id FROM hadiths WHERE arabic_text = %s LIMIT 1
                        """, (arabic_text,))
                        
                        existing = cursor.fetchone()
                        
                        if existing:
                            hadith_db_id = existing[0]
                            # Update last_imported_at
                            cursor.execute("""
                                UPDATE hadiths 
                                SET last_imported_at = NOW() 
                                WHERE id = %s
                            """, (hadith_db_id,))
                        else:
                            # Insert new hadith
                            cursor.execute("""
                                INSERT INTO hadiths (
                                    book_id, chapter_id, hadith_number, arabic_text,
                                    grade, explanation, hints, word_meanings, `references`,
                                    source, external_id, last_imported_at
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'hadeethenc', %s, NOW())
                            """, (book_id, 1, str(hadith_id_api), arabic_text, 
                                  grade, explanation, hints_text, meanings_text, refs_text, 
                                  str(hadith_id_api)))
                            
                            hadith_db_id = cursor.lastrowid
                            total_imported += 1
                            imported_in_category += 1
                        
                        # Link to category
                        cursor.execute("""
                            INSERT INTO hadith_category (hadith_id, category_id, last_imported_at)
                            VALUES (%s, %s, NOW())
                            ON DUPLICATE KEY UPDATE last_imported_at = NOW()
                        """, (hadith_db_id, cat_id))
                        
                        # Import translations for key languages
                        key_languages = ['en', 'vi', 'ur', 'bn', 'tr']  # Limit to key languages
                        for lang_code in key_languages:
                            if lang_code == 'ar':  # Already have Arabic
                                continue
                            
                            # Check if translation exists
                            cursor.execute("""
                                SELECT id FROM hadith_translations 
                                WHERE hadith_id = %s AND language_code = %s
                                LIMIT 1
                            """, (hadith_db_id, lang_code))
                            
                            if cursor.fetchone():
                                # Update last_imported_at
                                cursor.execute("""
                                    UPDATE hadith_translations 
                                    SET last_imported_at = NOW() 
                                    WHERE hadith_id = %s AND language_code = %s
                                """, (hadith_db_id, lang_code))
                                continue
                            
                            # Fetch translation
                            lang_url = API_ENDPOINTS['hadeethenc']['hadith_detail'].format(
                                language=lang_code, 
                                hadith_id=hadith_id_api
                            )
                            lang_data = fetch_json(lang_url)
                            
                            if lang_data and lang_data.get('hadeeth'):
                                trans_text = lang_data.get('hadeeth', '')
                                trans_explanation = lang_data.get('explanation', '')
                                
                                # Process hints for this language
                                trans_hints = lang_data.get('hints', [])
                                if trans_hints and isinstance(trans_hints, list):
                                    trans_hints_text = '\n'.join([f"- {hint}" for hint in trans_hints if hint])
                                else:
                                    trans_hints_text = None
                                
                                # Process references for this language
                                trans_refs = lang_data.get('references', [])
                                if trans_refs and isinstance(trans_refs, list):
                                    trans_refs_text = '\n'.join([f"- {ref}" for ref in trans_refs if ref])
                                else:
                                    trans_refs_text = lang_data.get('attribution', '')
                                
                                cursor.execute("""
                                    INSERT INTO hadith_translations (
                                        hadith_id, language_code, translation_text,
                                        explanation, hints, `references`, source, last_imported_at
                                    ) VALUES (%s, %s, %s, %s, %s, %s, 'hadeethenc', NOW())
                                """, (hadith_db_id, lang_code, trans_text,
                                      trans_explanation, trans_hints_text, trans_refs_text))
                        
                        conn.commit()
                        
                    except Exception as e:
                        log(f"Error importing hadith {hadith_id_api}: {e}", "ERROR")
                        conn.rollback()
                        continue
                
                # Check if more pages
                meta = hadiths_data.get('meta', {})
                last_page = int(meta.get('last_page', 0))
                
                if page >= last_page or len(hadith_list) < 20:
                    break
                
                page += 1
                time.sleep(0.5)  # Rate limiting
            
            # Update category timestamp
            cursor.execute("""
                UPDATE categories 
                SET last_imported_at = NOW(),
                    total_hadith = (
                        SELECT COUNT(*) 
                        FROM hadith_category hc 
                        WHERE hc.category_id = %s
                    )
                WHERE id = %s
            """, (cat_id, cat_id))
            
            conn.commit()
            log(f"Imported {imported_in_category} hadiths for category {cat_name}", "INFO")
            
        except Exception as e:
            log(f"Error processing category {cat_info.get('id')}: {e}", "ERROR")
            continue
    
    # Update book timestamp
    cursor.execute("""
        UPDATE books 
        SET last_imported_at = NOW(),
            total_hadith = (
                SELECT COUNT(*) FROM hadiths WHERE book_id = %s
            )
        WHERE id = %s
    """, (book_id, book_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log(f"Finished importing HadeethEnc: {total_imported} hadiths", "SUCCESS")
    return True

# ==================== STEP 4: DATA VERIFICATION AND CLEANUP ====================

def verify_and_cleanup_data():
    """Verify data integrity and clean up duplicates"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    log("Starting data verification and cleanup...", "INFO")
    
    # 1. Update book statistics
    cursor.execute("""
        UPDATE books b
        SET total_hadith = (
            SELECT COUNT(*) FROM hadiths h WHERE h.book_id = b.id
        ),
        updated_at = NOW()
    """)
    
    # 2. Update chapter statistics
    cursor.execute("""
        UPDATE chapters c
        SET total_hadith = (
            SELECT COUNT(*) FROM hadiths h WHERE h.chapter_id = c.id
        ),
        updated_at = NOW()
    """)
    
    # 3. Update category statistics
    cursor.execute("""
        UPDATE categories c
        SET total_hadith = (
            SELECT COUNT(*) FROM hadith_category hc WHERE hc.category_id = c.id
        ),
        updated_at = NOW()
    """)
    
    # 4. Remove duplicate hadiths (same Arabic text in same book)
    log("Checking for duplicate hadiths...", "INFO")
    cursor.execute("""
        DELETE h1 FROM hadiths h1
        INNER JOIN hadiths h2 
        WHERE 
            h1.id < h2.id AND 
            h1.book_id = h2.book_id AND 
            h1.arabic_text = h2.arabic_text
    """)
    duplicates_removed = cursor.rowcount
    if duplicates_removed > 0:
        log(f"Removed {duplicates_removed} duplicate hadiths", "INFO")
    
    # 5. Remove orphaned translations
    log("Checking for orphaned translations...", "INFO")
    cursor.execute("""
        DELETE ht FROM hadith_translations ht
        LEFT JOIN hadiths h ON ht.hadith_id = h.id
        WHERE h.id IS NULL
    """)
    orphans_removed = cursor.rowcount
    if orphans_removed > 0:
        log(f"Removed {orphans_removed} orphaned translations", "INFO")
    
    # 6. Remove orphaned category mappings
    log("Checking for orphaned category mappings...", "INFO")
    cursor.execute("""
        DELETE hc FROM hadith_category hc
        LEFT JOIN hadiths h ON hc.hadith_id = h.id
        WHERE h.id IS NULL
    """)
    orphan_mappings_removed = cursor.rowcount
    if orphan_mappings_removed > 0:
        log(f"Removed {orphan_mappings_removed} orphaned category mappings", "INFO")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log("Data verification and cleanup completed", "SUCCESS")

# ==================== STEP 5: EXPORT FOR FRONTEND (OPTIONAL) ====================

def convert_to_serializable(obj):
    """Convert non-serializable objects to serializable format"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')
    elif hasattr(obj, '__dict__'):
        return {k: convert_to_serializable(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_to_serializable(item) for item in obj)
    else:
        return obj

def export_data_for_frontend():
    """Export data to JSON format for frontend backup"""
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)
    
    # Export books
    cursor.execute("SELECT * FROM books ORDER BY id")
    books = cursor.fetchall()
    
    # Convert datetime objects to strings
    serializable_books = convert_to_serializable(books)
    
    with open(f"{export_dir}/books.json", 'w', encoding='utf-8') as f:
        json.dump(serializable_books, f, ensure_ascii=False, indent=2)
    
    # Export categories with tree structure
    cursor.execute("""
        SELECT id, parent_id, name_en, name_ar, total_hadith, slug 
        FROM categories 
        ORDER BY parent_id, id
    """)
    categories = cursor.fetchall()
    
    # Convert datetime objects to strings
    serializable_categories = convert_to_serializable(categories)
    
    # Build tree structure
    category_tree = build_category_tree(serializable_categories)
    
    with open(f"{export_dir}/categories_tree.json", 'w', encoding='utf-8') as f:
        json.dump(category_tree, f, ensure_ascii=False, indent=2)
    
    # Export sample hadiths for testing
    cursor.execute("""
        SELECT h.*, b.name_en as book_name, c.name_en as chapter_name
        FROM hadiths h
        LEFT JOIN books b ON h.book_id = b.id
        LEFT JOIN chapters c ON h.chapter_id = c.id
        LIMIT 100
    """)
    sample_hadiths = cursor.fetchall()
    
    # Convert datetime objects to strings
    serializable_hadiths = convert_to_serializable(sample_hadiths)
    
    with open(f"{export_dir}/sample_hadiths.json", 'w', encoding='utf-8') as f:
        json.dump(serializable_hadiths, f, ensure_ascii=False, indent=2)
    
    log(f"Exported {len(books)} books, {len(categories)} categories, {len(sample_hadiths)} sample hadiths", "INFO")
    
    cursor.close()
    conn.close()

def build_category_tree(categories):
    """Build hierarchical category tree"""
    category_map = {}
    root_categories = []
    
    # Create map
    for cat in categories:
        cat_id = cat['id']
        category_map[cat_id] = {
            'id': cat_id,
            'parent_id': cat['parent_id'],
            'name_en': cat['name_en'],
            'name_ar': cat['name_ar'],
            'total_hadith': cat['total_hadith'],
            'slug': cat['slug'],
            'children': []
        }
    
    # Build tree
    for cat_id, cat_data in category_map.items():
        parent_id = cat_data['parent_id']
        
        if parent_id is None or parent_id not in category_map:
            root_categories.append(cat_data)
        else:
            if 'children' not in category_map[parent_id]:
                category_map[parent_id]['children'] = []
            category_map[parent_id]['children'].append(cat_data)
    
    return root_categories

# ==================== SIMPLIFIED CLEANUP FUNCTION ====================

def cleanup_existing_tables():
    """Clean up existing tables before creating new ones"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Disable foreign key checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    
    # Drop tables in correct order (reverse of creation order)
    tables = [
        'hadith_reference_translations',
        'hadith_translations',
        'hadith_category',
        'hadiths',
        'chapters',
        'categories',
        'books'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            log(f"Dropped table: {table}", "INFO")
        except Exception as e:
            log(f"Could not drop {table}: {e}", "WARNING")
    
    # Re-enable foreign key checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log("Database cleanup completed", "SUCCESS")

# ==================== ALTERNATIVE: CREATE TABLES WITH FOREIGN KEYS LATER ====================

def create_tables_without_foreign_keys_first():
    """Create tables first, then add foreign keys separately"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Disable foreign key checks temporarily
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    
    # 1. Books table (no dependencies)
    log("Creating books table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INT PRIMARY KEY AUTO_INCREMENT,
            code VARCHAR(50) UNIQUE NOT NULL,
            name_en VARCHAR(255) NOT NULL,
            name_ar VARCHAR(255),
            total_hadith INT DEFAULT 0,
            source VARCHAR(50) NOT NULL DEFAULT 'fawaz',
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_code (code),
            INDEX idx_source (source)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 2. Categories table WITHOUT foreign key first
    log("Creating categories table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INT PRIMARY KEY AUTO_INCREMENT,
            parent_id INT DEFAULT NULL,
            name_en VARCHAR(255) NOT NULL,
            name_ar VARCHAR(255),
            total_hadith INT DEFAULT 0,
            slug VARCHAR(255) UNIQUE,
            source VARCHAR(50) NOT NULL DEFAULT 'hadeethenc',
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_parent_id (parent_id),
            INDEX idx_slug (slug),
            INDEX idx_source (source)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 3. Chapters table WITHOUT foreign key first
    log("Creating chapters table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chapters (
            id INT PRIMARY KEY AUTO_INCREMENT,
            book_id INT NOT NULL,
            chapter_no INT NOT NULL,
            name_en VARCHAR(255) NOT NULL,
            name_ar VARCHAR(255),
            total_hadith INT DEFAULT 0,
            source VARCHAR(50) NOT NULL DEFAULT 'fawaz',
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_book_chapter (book_id, chapter_no),
            INDEX idx_book_id (book_id),
            INDEX idx_source (source)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 4. Main hadiths table WITHOUT foreign keys first
    log("Creating hadiths table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hadiths (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            book_id INT NOT NULL,
            chapter_id INT NOT NULL,
            hadith_number VARCHAR(50) NOT NULL,
            arabic_text LONGTEXT NOT NULL,
            grade VARCHAR(100),
            explanation LONGTEXT,
            hints LONGTEXT,
            word_meanings LONGTEXT,
            `references` LONGTEXT,
            narrator VARCHAR(500),
            source VARCHAR(50) NOT NULL DEFAULT 'fawaz',
            external_id VARCHAR(100),
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_book_chapter (book_id, chapter_id),
            INDEX idx_hadith_number (hadith_number),
            INDEX idx_source (source),
            INDEX idx_external_id (external_id),
            FULLTEXT idx_arabic_text (arabic_text)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 5. Translations table WITHOUT foreign key first
    log("Creating translations table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hadith_translations (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            hadith_id BIGINT NOT NULL,
            language_code VARCHAR(10) NOT NULL,
            translation_text LONGTEXT NOT NULL,
            explanation LONGTEXT,
            hints LONGTEXT,
            `references` LONGTEXT,
            narrator VARCHAR(500),
            source VARCHAR(50) NOT NULL DEFAULT 'fawaz',
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_hadith_language (hadith_id, language_code),
            INDEX idx_language (language_code),
            INDEX idx_source (source),
            FULLTEXT idx_translation_text (translation_text)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 6. Hadith-Category mapping WITHOUT foreign keys first
    log("Creating hadith_category mapping table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hadith_category (
            hadith_id BIGINT NOT NULL,
            category_id INT NOT NULL,
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (hadith_id, category_id),
            INDEX idx_category_id (category_id),
            INDEX idx_hadith_id (hadith_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    # 7. Reference translations table WITHOUT foreign key first
    log("Creating reference translations table...", "INFO")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hadith_reference_translations (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            hadith_id BIGINT NOT NULL,
            language_code VARCHAR(10) NOT NULL,
            `references` LONGTEXT,
            last_imported_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY idx_hadith_lang (hadith_id, language_code),
            INDEX idx_hadith_id (hadith_id),
            INDEX idx_language_code (language_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Now add foreign keys separately
    add_foreign_keys()
    
    log("Database structure created successfully", "SUCCESS")
    return True

def add_foreign_keys():
    """Add foreign keys after tables are created"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Disable foreign key checks temporarily
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    
    try:
        # 1. Add foreign key to categories table (self-referencing)
        log("Adding foreign key to categories table...", "INFO")
        cursor.execute("""
            ALTER TABLE categories 
            ADD CONSTRAINT fk_categories_parent 
            FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
        """)
    except Exception as e:
        log(f"Could not add foreign key to categories: {e}", "WARNING")
    
    try:
        # 2. Add foreign key to chapters table
        log("Adding foreign key to chapters table...", "INFO")
        cursor.execute("""
            ALTER TABLE chapters 
            ADD CONSTRAINT fk_chapters_books 
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        """)
    except Exception as e:
        log(f"Could not add foreign key to chapters: {e}", "WARNING")
    
    try:
        # 3. Add foreign keys to hadiths table
        log("Adding foreign keys to hadiths table...", "INFO")
        cursor.execute("""
            ALTER TABLE hadiths 
            ADD CONSTRAINT fk_hadiths_books 
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        """)
        
        cursor.execute("""
            ALTER TABLE hadiths 
            ADD CONSTRAINT fk_hadiths_chapters 
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
        """)
    except Exception as e:
        log(f"Could not add foreign keys to hadiths: {e}", "WARNING")
    
    try:
        # 4. Add foreign key to translations table
        log("Adding foreign key to translations table...", "INFO")
        cursor.execute("""
            ALTER TABLE hadith_translations 
            ADD CONSTRAINT fk_translations_hadiths 
            FOREIGN KEY (hadith_id) REFERENCES hadiths(id) ON DELETE CASCADE
        """)
    except Exception as e:
        log(f"Could not add foreign key to translations: {e}", "WARNING")
    
    try:
        # 5. Add foreign keys to hadith_category table
        log("Adding foreign keys to hadith_category table...", "INFO")
        cursor.execute("""
            ALTER TABLE hadith_category 
            ADD CONSTRAINT fk_hadith_category_hadiths 
            FOREIGN KEY (hadith_id) REFERENCES hadiths(id) ON DELETE CASCADE
        """)
        
        cursor.execute("""
            ALTER TABLE hadith_category 
            ADD CONSTRAINT fk_hadith_category_categories 
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        """)
    except Exception as e:
        log(f"Could not add foreign keys to hadith_category: {e}", "WARNING")
    
    try:
        # 6. Add foreign key to reference translations table
        log("Adding foreign key to reference translations table...", "INFO")
        cursor.execute("""
            ALTER TABLE hadith_reference_translations 
            ADD CONSTRAINT fk_ref_translations_hadiths 
            FOREIGN KEY (hadith_id) REFERENCES hadiths(id) ON DELETE CASCADE
        """)
    except Exception as e:
        log(f"Could not add foreign key to reference translations: {e}", "WARNING")
    
    # Re-enable foreign key checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    log("Foreign keys added successfully", "SUCCESS")
    return True

# ==================== SHOW DATABASE STATISTICS ====================

def show_database_statistics():
    """Display current database statistics"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("\n" + "=" * 80)
    print("CURRENT DATABASE STATISTICS")
    print("=" * 80)
    
    try:
        # Total books
        cursor.execute("SELECT COUNT(*) FROM books")
        total_books = cursor.fetchone()[0]
        print(f"Total Books: {total_books}")
        
        # Books by source
        cursor.execute("SELECT source, COUNT(*) FROM books GROUP BY source")
        print("Books by Source:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]}")
        
        # Total hadiths
        cursor.execute("SELECT COUNT(*) FROM hadiths")
        total_hadiths = cursor.fetchone()[0]
        print(f"\nTotal Hadiths: {total_hadiths}")
        
        # Hadiths by source
        cursor.execute("SELECT source, COUNT(*) FROM hadiths GROUP BY source")
        print("Hadiths by Source:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]}")
        
        # Total translations
        cursor.execute("SELECT COUNT(*) FROM hadith_translations")
        total_translations = cursor.fetchone()[0]
        print(f"\nTotal Translations: {total_translations}")
        
        # Translations by language
        cursor.execute("SELECT language_code, COUNT(*) FROM hadith_translations GROUP BY language_code ORDER BY COUNT(*) DESC")
        print("Translations by Language:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]}")
        
        # Total categories
        cursor.execute("SELECT COUNT(*) FROM categories")
        total_categories = cursor.fetchone()[0]
        print(f"\nTotal Categories: {total_categories}")
        
        # Total chapters
        cursor.execute("SELECT COUNT(*) FROM chapters")
        total_chapters = cursor.fetchone()[0]
        print(f"Total Chapters: {total_chapters}")
        
        # Last import timestamps
        print(f"\nLast Import Timestamps:")
        cursor.execute("SELECT code, last_imported_at FROM books WHERE last_imported_at IS NOT NULL ORDER BY last_imported_at DESC LIMIT 5")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]}")
        
        # Average translations per hadith
        if total_hadiths > 0:
            avg_translations = total_translations / total_hadiths
            print(f"\nAverage Translations per Hadith: {avg_translations:.1f}")
        
        # Top 5 categories by hadith count
        cursor.execute("""
            SELECT c.name_en, COUNT(hc.hadith_id) as hadith_count
            FROM categories c
            LEFT JOIN hadith_category hc ON c.id = hc.category_id
            GROUP BY c.id
            ORDER BY hadith_count DESC
            LIMIT 5
        """)
        print(f"\nTop 5 Categories by Hadith Count:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]} hadiths")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"Error getting statistics: {e}")
    
    cursor.close()
    conn.close()

# ==================== CHECK MISSING DATA ====================

def check_missing_data():
    """Check for missing data in the database"""
    
    print("\n" + "=" * 80)
    print("CHECKING FOR MISSING DATA")
    print("=" * 80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Check books without last_imported_at
        cursor.execute("SELECT COUNT(*) FROM books WHERE last_imported_at IS NULL")
        books_without_import = cursor.fetchone()[0]
        print(f"Books never imported: {books_without_import}")
        
        if books_without_import > 0:
            cursor.execute("SELECT code, name_en FROM books WHERE last_imported_at IS NULL")
            for row in cursor.fetchall():
                print(f"  - {row[0]} ({row[1]})")
        
        # 2. Check categories without last_imported_at
        cursor.execute("SELECT COUNT(*) FROM categories WHERE last_imported_at IS NULL AND source = 'hadeethenc'")
        categories_without_import = cursor.fetchone()[0]
        print(f"\nHadeethEnc categories never imported: {categories_without_import}")
        
        # 3. Check hadiths without translations
        cursor.execute("""
            SELECT COUNT(*) 
            FROM hadiths h 
            LEFT JOIN hadith_translations ht ON h.id = ht.hadith_id 
            WHERE ht.id IS NULL
        """)
        hadiths_without_translations = cursor.fetchone()[0]
        print(f"\nHadiths without any translations: {hadiths_without_translations}")
        
        # 4. Check for books with few hadiths
        cursor.execute("""
            SELECT b.code, b.name_en, COUNT(h.id) as hadith_count
            FROM books b
            LEFT JOIN hadiths h ON b.id = h.book_id
            GROUP BY b.id
            HAVING hadith_count < 100
            ORDER BY hadith_count ASC
        """)
        books_with_few_hadiths = cursor.fetchall()
        print(f"\nBooks with less than 100 hadiths: {len(books_with_few_hadiths)}")
        for row in books_with_few_hadiths:
            print(f"  - {row[0]} ({row[1]}): {row[2]} hadiths")
        
        # 5. Check for missing Fawaz hadiths
        print(f"\nChecking missing Fawaz hadiths:")
        for book_code in BOOK_MAPPING:
            if BOOK_MAPPING[book_code]['fawaz']:
                existing_count, missing = check_missing_fawaz_data(book_code, 100)
                if len(missing) > 0:
                    print(f"  - {book_code}: {len(missing)} missing (have {existing_count})")
                    if len(missing) <= 10:  # Show details if few missing
                        print(f"    Missing numbers: {missing[:10]}{'...' if len(missing) > 10 else ''}")
        
        # 6. Check for stale imports (older than 7 days)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM books 
            WHERE last_imported_at < DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        stale_books = cursor.fetchone()[0]
        print(f"\nBooks with stale imports (>7 days): {stale_books}")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM categories 
            WHERE source = 'hadeethenc' 
            AND last_imported_at < DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        stale_categories = cursor.fetchone()[0]
        print(f"HadeethEnc categories with stale imports (>7 days): {stale_categories}")
        
    except Exception as e:
        print(f"Error checking missing data: {e}")
    
    cursor.close()
    conn.close()
    
    print("=" * 80)

# ==================== MAIN EXECUTION ====================

def main():
    """Main execution function"""
    
    print("=" * 80)
    print("COMPLETE HADITH DATA IMPORT SCRIPT")
    print("Sources: Fawaz API + HadeethEnc API")
    print("=" * 80)
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Import hadith data from multiple sources')
    parser.add_argument('--step', type=int, choices=[1,2,3,4,5,6,7,8], 
                       help='Run specific step (1:DB, 2:Fawaz, 3:HadeethEnc, 4:Cleanup, 5:Export, 6:CreateDB, 7:Stats, 8:CheckMissing)')
    parser.add_argument('--book', type=str, 
                       help='Import specific book from Fawaz (e.g., bukhari, muslim)')
    parser.add_argument('--all-books', action='store_true',
                       help='Import all books from Fawaz')
    parser.add_argument('--max-hadiths', type=int, default=500,
                       help='Maximum hadiths per book to import (default: 500)')
    parser.add_argument('--skip-fawaz', action='store_true',
                       help='Skip Fawaz import')
    parser.add_argument('--skip-hadeethenc', action='store_true',
                       help='Skip HadeethEnc import')
    parser.add_argument('--full', action='store_true',
                       help='Run full import (all steps)')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up existing tables before starting (WARNING: deletes all data!)')
    parser.add_argument('--alt-db', action='store_true',
                       help='Use alternative database creation method')
    parser.add_argument('--skip-export', action='store_true',
                       help='Skip export step')
    parser.add_argument('--incremental', action='store_true',
                       help='Import only missing/updated data (recommended)')
    parser.add_argument('--force', action='store_true',
                       help='Force full import even if data exists')
    parser.add_argument('--show-apis', action='store_true',
                       help='Show all API endpoints')
    parser.add_argument('--category-limit', type=int, default=5,
                       help='Limit number of categories to import from HadeethEnc (default: 5)')
    
    args = parser.parse_args()
    
    # Show API endpoints if requested
    if args.show_apis:
        show_api_endpoints()
        return
    
    if args.full:
        # Run all steps
        args.step = None
        args.all_books = True
        args.skip_fawaz = False
        args.skip_hadeethenc = False
        args.incremental = False  # Full import should be complete
    
    try:
        # Optional cleanup (WARNING: this deletes all data!)
        if args.cleanup:
            log("WARNING: Cleaning up existing tables - ALL DATA WILL BE LOST!", "WARNING")
            confirm = input("Are you sure you want to delete all data? (yes/no): ")
            if confirm.lower() == 'yes':
                cleanup_existing_tables()
            else:
                log("Cleanup cancelled", "INFO")
                return
        
        # Step 1: Ensure database structure
        if not args.step or args.step == 1:
            log("Step 1: Ensuring database structure...", "INFO")
            if args.alt_db:
                create_tables_without_foreign_keys_first()
            else:
                ensure_database_structure()
        
        # Step 2: Import from Fawaz API
        if not args.skip_fawaz and (not args.step or args.step == 2):
            log("Step 2: Importing from Fawaz API...", "INFO")
            
            books_to_import = []
            if args.book:
                books_to_import = [args.book]
            elif args.all_books:
                books_to_import = list(BOOK_MAPPING.keys())
            else:
                # Default to major books
                books_to_import = ['bukhari', 'muslim']
            
            for book_code in books_to_import:
                if book_code in BOOK_MAPPING and BOOK_MAPPING[book_code]['fawaz']:
                    log(f"Importing {book_code}...", "INFO")
                    # Use incremental mode unless forced
                    incremental_mode = args.incremental and not args.force
                    import_fawaz_hadiths(book_code, args.max_hadiths, incremental=incremental_mode)
                    time.sleep(2)  # Rate limiting
        
        # Step 3: Import from HadeethEnc
        if not args.skip_hadeethenc and (not args.step or args.step == 3):
            log("Step 3: Importing from HadeethEnc...", "INFO")
            # Use incremental mode unless forced
            incremental_mode = args.incremental and not args.force
            import_hadeethenc_categories(incremental=incremental_mode, category_limit=args.category_limit)
        
        # Step 4: Verify and cleanup
        if not args.step or args.step == 4:
            log("Step 4: Verifying and cleaning up data...", "INFO")
            verify_and_cleanup_data()
        
        # Step 5: Export for frontend
        if not args.skip_export and (not args.step or args.step == 5):
            log("Step 5: Exporting data for frontend...", "INFO")
            export_data_for_frontend()
        
        # Step 6: Just create database structure
        if args.step == 6:
            log("Step 6: Just creating database structure...", "INFO")
            if args.alt_db:
                create_tables_without_foreign_keys_first()
            else:
                ensure_database_structure()
        
        # Step 7: Show statistics
        if args.step == 7 or (not args.step and not args.skip_fawaz and not args.skip_hadeethenc):
            show_database_statistics()
        
        # Step 8: Check missing data
        if args.step == 8:
            check_missing_data()
        
        log("Import completed successfully!", "SUCCESS")
        
        # Show final statistics if we did an import
        if not args.step or args.step in [1,2,3,4,5]:
            show_database_statistics()
        
    except KeyboardInterrupt:
        log("Import interrupted by user", "WARNING")
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()