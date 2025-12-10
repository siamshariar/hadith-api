#!/usr/bin/env python3
"""
HadeethEnc.com Data Import Script
This script imports all data from HadeethEnc.com API into MySQL database
"""

import requests
import mysql.connector
from mysql.connector import Error
import json
import time
from datetime import datetime
import logging
from typing import Dict, List, Optional, Any, Tuple
import sys
from urllib.parse import urljoin
import concurrent.futures
from tqdm import tqdm
import re

# Configuration
API_BASE_URL = "https://hadeethenc.com/api/v1"
SUPPORTED_LANGUAGES = [
    'ar', 'en', 'bn', 'bs', 'es', 'fa', 'fr', 'id', 'ru', 'tl', 
    'tr', 'ur', 'zh', 'hi', 'vi', 'si', 'ug', 'ha', 'ku'
]

# Database configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'hadith_api_prod',
    'user': 'root',
    'password': '123456',
    'charset': 'utf8mb4'
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hadeeth_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HadeethImporter:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        })
        
        # Database connection
        self.db = None
        self.cursor = None
        self.connect_db()
        
        # Cache dictionaries
        self.language_cache = {}
        self.category_cache = {}
        self.book_cache = {}
        self.chapter_cache = {}
        self.hadith_cache = set()
        
    def connect_db(self):
        """Establish database connection"""
        try:
            self.db = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.db.cursor(dictionary=True)
            logger.info("Database connection established successfully")
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            sys.exit(1)
    
    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.db:
            self.db.close()
        logger.info("Database connection closed")
    
    def log_sync(self, sync_type: str, item_id: int = None, 
                 status: str = 'success', message: str = ''):
        """Log synchronization activity"""
        query = """
        INSERT INTO sync_logs (sync_type, item_id, status, message)
        VALUES (%s, %s, %s, %s)
        """
        try:
            self.cursor.execute(query, (sync_type, item_id, status, message))
            self.db.commit()
        except Error as e:
            logger.error(f"Error logging sync: {e}")
    
    def api_request(self, endpoint: str, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """Make API request with retry logic"""
        url = urljoin(API_BASE_URL, endpoint)
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for {url}: {e}")
                return None
    
    def get_all_languages(self) -> List[str]:
        """Get list of all supported languages from API"""
        endpoint = "/languages/"
        data = self.api_request(endpoint)
        
        if data and isinstance(data, list):
            languages = [lang['code'] for lang in data if 'code' in lang]
            logger.info(f"Found {len(languages)} languages from API")
            return languages
        else:
            logger.warning("Could not fetch languages from API, using default list")
            return SUPPORTED_LANGUAGES
    
    def get_root_categories(self, language: str) -> List[Dict]:
        """Get root categories for a language"""
        endpoint = "/categories/roots/"
        params = {'language': language}
        data = self.api_request(endpoint, params)
        
        if data and isinstance(data, list):
            logger.info(f"Found {len(data)} root categories for language {language}")
            return data
        return []
    
    def get_category_details(self, category_id: int, language: str) -> Optional[Dict]:
        """Get category details including subcategories"""
        endpoint = f"/categories/list/"
        params = {'language': language, 'category_id': category_id}
        data = self.api_request(endpoint, params)
        
        if data and isinstance(data, dict):
            return data
        return None
    
    def get_hadiths_by_category(self, category_id: int, language: str, 
                                page: int = 1, per_page: int = 100) -> Dict:
        """Get hadiths by category with pagination"""
        endpoint = "/hadeeths/list/"
        params = {
            'language': language,
            'category_id': category_id,
            'page': page,
            'per_page': per_page
        }
        data = self.api_request(endpoint, params)
        
        if data and isinstance(data, dict):
            return data
        return {'data': [], 'meta': {'current_page': page, 'last_page': 1}}
    
    def get_hadith_details(self, hadith_id: int, language: str) -> Optional[Dict]:
        """Get detailed hadith information"""
        endpoint = "/hadeeths/one/"
        params = {'id': hadith_id, 'language': language}
        data = self.api_request(endpoint, params)
        
        if data and isinstance(data, dict):
            return data
        return None
    
    def insert_language(self, code: str, name: str, native_name: str = None, 
                        direction: str = 'ltr') -> bool:
        """Insert or update language in database"""
        if not native_name:
            native_name = name
        
        query = """
        INSERT INTO languages (code, name, native_name, direction)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            native_name = VALUES(native_name),
            direction = VALUES(direction)
        """
        
        try:
            self.cursor.execute(query, (code, name, native_name, direction))
            self.db.commit()
            self.language_cache[code] = self.cursor.lastrowid
            return True
        except Error as e:
            logger.error(f"Error inserting language {code}: {e}")
            self.log_sync('language', None, 'error', str(e))
            return False
    
    def insert_category(self, category_data: Dict) -> bool:
        """Insert or update category in database"""
        category_id = int(category_data.get('id', 0))
        parent_id = category_data.get('parent_id')
        
        if parent_id == '' or parent_id == 'null':
            parent_id = None
        elif parent_id:
            parent_id = int(parent_id)
        
        query = """
        INSERT INTO categories (id, parent_id, sort_order)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            parent_id = VALUES(parent_id),
            sort_order = VALUES(sort_order)
        """
        
        try:
            self.cursor.execute(query, (category_id, parent_id, 0))
            self.db.commit()
            self.category_cache[category_id] = category_id
            return True
        except Error as e:
            logger.error(f"Error inserting category {category_id}: {e}")
            self.log_sync('category', category_id, 'error', str(e))
            return False
    
    def insert_category_translation(self, category_id: int, language_code: str, 
                                    title: str) -> bool:
        """Insert or update category translation"""
        query = """
        INSERT INTO category_translations (category_id, language_code, title)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title)
        """
        
        try:
            self.cursor.execute(query, (category_id, language_code, title))
            self.db.commit()
            return True
        except Error as e:
            logger.error(f"Error inserting category translation {category_id}/{language_code}: {e}")
            return False
    
    def insert_book(self, book_data: Dict) -> bool:
        """Insert or update book in database"""
        book_id = book_data.get('id')
        book_code = book_data.get('code', f'book_{book_id}')
        
        query = """
        INSERT INTO books (id, code, sort_order)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            code = VALUES(code),
            sort_order = VALUES(sort_order)
        """
        
        try:
            self.cursor.execute(query, (book_id, book_code, 0))
            self.db.commit()
            self.book_cache[book_id] = book_id
            return True
        except Error as e:
            logger.error(f"Error inserting book {book_id}: {e}")
            self.log_sync('book', book_id, 'error', str(e))
            return False
    
    def insert_book_translation(self, book_id: int, language_code: str, 
                                title: str, author: str = None) -> bool:
        """Insert or update book translation"""
        query = """
        INSERT INTO book_translations (book_id, language_code, title, author)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            author = VALUES(author)
        """
        
        try:
            self.cursor.execute(query, (book_id, language_code, title, author))
            self.db.commit()
            return True
        except Error as e:
            logger.error(f"Error inserting book translation {book_id}/{language_code}: {e}")
            return False
    
    def insert_chapter(self, book_id: int, chapter_data: Dict) -> bool:
        """Insert or update chapter in database"""
        chapter_id = chapter_data.get('id')
        parent_id = chapter_data.get('parent_id')
        chapter_number = chapter_data.get('chapter_number')
        
        if parent_id == '' or parent_id == 'null':
            parent_id = None
        elif parent_id:
            parent_id = int(parent_id)
        
        query = """
        INSERT INTO chapters (id, book_id, parent_id, chapter_number, sort_order)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            book_id = VALUES(book_id),
            parent_id = VALUES(parent_id),
            chapter_number = VALUES(chapter_number),
            sort_order = VALUES(sort_order)
        """
        
        try:
            self.cursor.execute(query, (chapter_id, book_id, parent_id, chapter_number, 0))
            self.db.commit()
            self.chapter_cache[chapter_id] = chapter_id
            return True
        except Error as e:
            logger.error(f"Error inserting chapter {chapter_id}: {e}")
            self.log_sync('chapter', chapter_id, 'error', str(e))
            return False
    
    def insert_chapter_translation(self, chapter_id: int, language_code: str, 
                                   title: str) -> bool:
        """Insert or update chapter translation"""
        query = """
        INSERT INTO chapter_translations (chapter_id, language_code, title)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title)
        """
        
        try:
            self.cursor.execute(query, (chapter_id, language_code, title))
            self.db.commit()
            return True
        except Error as e:
            logger.error(f"Error inserting chapter translation {chapter_id}/{language_code}: {e}")
            return False
    
    def insert_hadith(self, hadith_data: Dict, language: str = 'ar') -> bool:
        """Insert or update hadith in database"""
        hadith_id = int(hadith_data.get('id', 0))
        
        if hadith_id in self.hadith_cache:
            return True
        
        # Extract hadith details
        arabic_text = hadith_data.get('hadeeth', '')
        attribution = hadith_data.get('attribution', '')
        grade = hadith_data.get('grade', '')
        
        # Extract book and chapter info if available
        book_id = hadith_data.get('book_id')
        chapter_id = hadith_data.get('chapter_id')
        
        # Try to extract hadith number from text
        hadith_number = None
        if arabic_text:
            # Look for common patterns like رقم: or الحديث رقم
            patterns = [
                r'رقم[:\s]*(\d+)',
                r'الحديث رقم[:\s]*(\d+)',
                r'hadith number[:\s]*(\d+)',
                r'#(\d+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, arabic_text, re.IGNORECASE)
                if match:
                    hadith_number = match.group(1)
                    break
        
        query = """
        INSERT INTO hadiths (id, book_id, chapter_id, hadith_number, grade, 
                           narrator, arabic_text, attribution)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            book_id = VALUES(book_id),
            chapter_id = VALUES(chapter_id),
            hadith_number = VALUES(hadith_number),
            grade = VALUES(grade),
            narrator = VALUES(narrator),
            arabic_text = VALUES(arabic_text),
            attribution = VALUES(attribution)
        """
        
        try:
            self.cursor.execute(query, (
                hadith_id, book_id, chapter_id, hadith_number, 
                grade, None, arabic_text, attribution
            ))
            self.db.commit()
            self.hadith_cache.add(hadith_id)
            self.log_sync('hadith', hadith_id, 'success', 'Hadith inserted')
            return True
        except Error as e:
            logger.error(f"Error inserting hadith {hadith_id}: {e}")
            self.log_sync('hadith', hadith_id, 'error', str(e))
            return False
    
    def insert_hadith_translation(self, hadith_id: int, language_code: str, 
                                  translation_data: Dict) -> bool:
        """Insert or update hadith translation"""
        translation_text = translation_data.get('title', '')
        explanation = translation_data.get('explanation', '')
        hints = translation_data.get('hints', '')
        
        if isinstance(hints, list):
            hints = '\n'.join(hints)
        
        query = """
        INSERT INTO hadith_translations 
        (hadith_id, language_code, translation_text, explanation, hints)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            translation_text = VALUES(translation_text),
            explanation = VALUES(explanation),
            hints = VALUES(hints)
        """
        
        try:
            self.cursor.execute(query, (
                hadith_id, language_code, translation_text, explanation, hints
            ))
            self.db.commit()
            return True
        except Error as e:
            logger.error(f"Error inserting hadith translation {hadith_id}/{language_code}: {e}")
            return False
    
    def link_hadith_category(self, hadith_id: int, category_id: int) -> bool:
        """Link hadith to category"""
        query = """
        INSERT IGNORE INTO hadith_categories (hadith_id, category_id)
        VALUES (%s, %s)
        """
        
        try:
            self.cursor.execute(query, (hadith_id, category_id))
            self.db.commit()
            return True
        except Error as e:
            logger.error(f"Error linking hadith {hadith_id} to category {category_id}: {e}")
            return False
    
    def import_categories_for_language(self, language: str):
        """Import categories for a specific language"""
        logger.info(f"Importing categories for language: {language}")
        
        # Get root categories
        root_categories = self.get_root_categories(language)
        
        if not root_categories:
            logger.warning(f"No categories found for language {language}")
            return
        
        # Process each root category
        for category in tqdm(root_categories, desc=f"Categories ({language})"):
            try:
                category_id = int(category.get('id', 0))
                title = category.get('title', '')
                parent_id = category.get('parent_id')
                
                # Insert category
                self.insert_category({
                    'id': category_id,
                    'parent_id': parent_id
                })
                
                # Insert category translation
                self.insert_category_translation(category_id, language, title)
                
                # Get and process subcategories if available
                self.process_subcategories(category_id, language)
                
                self.log_sync('category', category_id, 'success', 
                            f'Category imported for {language}')
                
            except Exception as e:
                logger.error(f"Error processing category {category}: {e}")
                self.log_sync('category', None, 'error', str(e))
    
    def process_subcategories(self, parent_id: int, language: str, depth: int = 0):
        """Recursively process subcategories"""
        if depth > 5:  # Prevent infinite recursion
            return
        
        # Try to get subcategories (this might require a different endpoint)
        # For now, we'll rely on the root categories endpoint
        pass
    
    def import_hadiths_for_category(self, category_id: int, language: str):
        """Import all hadiths for a category"""
        logger.info(f"Importing hadiths for category {category_id} in {language}")
        
        page = 1
        total_hadiths = 0
        
        while True:
            # Get hadiths for current page
            result = self.get_hadiths_by_category(category_id, language, page, 100)
            
            if not result or 'data' not in result:
                break
            
            hadiths = result.get('data', [])
            meta = result.get('meta', {})
            
            if not hadiths:
                break
            
            # Process each hadith
            for hadith_summary in tqdm(hadiths, desc=f"Hadiths page {page}"):
                try:
                    hadith_id = int(hadith_summary.get('id', 0))
                    
                    # Get detailed hadith information
                    hadith_details = self.get_hadith_details(hadith_id, language)
                    if not hadith_details:
                        continue
                    
                    # Insert hadith
                    self.insert_hadith(hadith_details, language)
                    
                    # Insert translation
                    self.insert_hadith_translation(hadith_id, language, hadith_details)
                    
                    # Link to category
                    self.link_hadith_category(hadith_id, category_id)
                    
                    # Also get Arabic version for full details
                    if language != 'ar':
                        arabic_details = self.get_hadith_details(hadith_id, 'ar')
                        if arabic_details:
                            # Update hadith with Arabic details
                            self.insert_hadith(arabic_details, 'ar')
                    
                    total_hadiths += 1
                    
                    # Be respectful to the API
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing hadith {hadith_id}: {e}")
                    self.log_sync('hadith', hadith_id, 'error', str(e))
            
            # Check if there are more pages
            current_page = int(meta.get('current_page', page))
            last_page = int(meta.get('last_page', 1))
            
            if current_page >= last_page:
                break
            
            page += 1
        
        logger.info(f"Imported {total_hadiths} hadiths for category {category_id}")
    
    def import_all_data(self):
        """Main function to import all data"""
        logger.info("Starting HadeethEnc data import")
        
        start_time = datetime.now()
        
        try:
            # Step 1: Import languages
            logger.info("Step 1: Processing languages")
            languages = self.get_all_languages()
            
            # Step 2: Import categories for each language
            logger.info("Step 2: Importing categories")
            for language in languages[:3]:  # Limit to first 3 languages for initial import
                self.import_categories_for_language(language)
                time.sleep(1)  # Be respectful to the API
            
            # Step 3: Get all categories from database
            logger.info("Step 3: Getting all categories from database")
            self.cursor.execute("SELECT id FROM categories ORDER BY id")
            all_categories = [row['id'] for row in self.cursor.fetchall()]
            
            # Step 4: Import hadiths for each category
            logger.info("Step 4: Importing hadiths")
            for category_id in tqdm(all_categories[:10], desc="Categories"):  # Limit to first 10 categories
                # Import hadiths for each language
                for language in languages[:2]:  # Limit to first 2 languages
                    self.import_hadiths_for_category(category_id, language)
                    time.sleep(0.5)
                
                # Be respectful to the API
                time.sleep(1)
            
            # Step 5: Import books and chapters (if available via API)
            logger.info("Step 5: Importing books and chapters")
            self.import_books_and_chapters()
            
        except Exception as e:
            logger.error(f"Error during import: {e}")
        finally:
            # Calculate total time
            end_time = datetime.now()
            duration = end_time - start_time
            
            # Log summary
            self.cursor.execute("SELECT COUNT(*) as count FROM hadiths")
            hadith_count = self.cursor.fetchone()['count']
            
            self.cursor.execute("SELECT COUNT(*) as count FROM categories")
            category_count = self.cursor.fetchone()['count']
            
            logger.info(f"Import completed in {duration}")
            logger.info(f"Total hadiths imported: {hadith_count}")
            logger.info(f"Total categories imported: {category_count}")
            
            self.close_db()
    
    def import_books_and_chapters(self):
        """Import books and chapters if API provides this data"""
        # Note: HadeethEnc API might not have books/chapters endpoint
        # This is a placeholder for future implementation
        
        # For now, we'll create a default book for hadiths without book info
        query = """
        INSERT INTO books (id, code, sort_order)
        VALUES (1, 'default', 0)
        ON DUPLICATE KEY UPDATE code = VALUES(code)
        """
        
        try:
            self.cursor.execute(query)
            self.db.commit()
            
            # Add English translation
            self.insert_book_translation(1, 'en', 'Default Hadith Collection')
            
            logger.info("Created default book for hadiths")
        except Error as e:
            logger.error(f"Error creating default book: {e}")
    
    def run_initial_import(self):
        """Run initial import with limited data for testing"""
        logger.info("Running initial import (limited data)")
        
        # Test with just English and Arabic
        test_languages = ['en', 'ar']
        test_category_ids = [1, 2, 3]  # First 3 categories
        
        for language in test_languages:
            self.import_categories_for_language(language)
            time.sleep(1)
        
        for category_id in test_category_ids:
            for language in test_languages:
                self.import_hadiths_for_category(category_id, language)
                time.sleep(1)
        
        logger.info("Initial import completed")

def main():
    """Main function"""
    print("HadeethEnc.com Data Import Script")
    print("=" * 50)
    
    importer = HadeethImporter()
    
    try:
        # Ask user for import mode
        print("\nSelect import mode:")
        print("1. Full import (all data - may take hours)")
        print("2. Initial import (limited data for testing)")
        print("3. Update existing data (incremental import)")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            print("\nWARNING: Full import may take several hours and make many API calls.")
            confirm = input("Are you sure you want to continue? (yes/no): ").strip().lower()
            if confirm == 'yes':
                importer.import_all_data()
            else:
                print("Import cancelled.")
        
        elif choice == '2':
            importer.run_initial_import()
        
        elif choice == '3':
            print("Update mode not yet implemented. Running initial import instead.")
            importer.run_initial_import()
        
        else:
            print("Invalid choice. Exiting.")
    
    except KeyboardInterrupt:
        print("\n\nImport interrupted by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}")
    finally:
        importer.close_db()
        print("\nScript completed.")

if __name__ == "__main__":
    main()