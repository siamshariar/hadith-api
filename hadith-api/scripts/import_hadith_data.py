#!/usr/bin/env python3
"""
Improved Hadith Data Import Script with Better Error Handling
"""

import json
import requests
import mysql.connector
from mysql.connector import Error
import time
import sys
import os
from datetime import datetime
import traceback

# Database Configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'hadith_api_prod',
    'user': 'root',
    'password': '123456'
}

# API Sources with fallbacks
FAWAZ_API_BASE = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1"
HADEETHENC_API = "https://hadeethenc.com/api/v1"

# Local cache directory
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

class ImprovedHadithImporter:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect_db()
        
    def connect_db(self):
        """Establish database connection"""
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True)
            print("✅ Database connected successfully")
        except Error as e:
            print(f"❌ Error connecting to database: {e}")
            sys.exit(1)
    
    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ Database connection closed")
    
    def execute_query(self, query, params=None, commit=False):
        """Execute SQL query with better error handling"""
        try:
            self.cursor.execute(query, params or ())
            if commit:
                self.conn.commit()
            return self.cursor
        except Error as e:
            print(f"❌ Query error: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            return None
    
    def fetch_with_cache(self, url, cache_name, timeout=60):
        """Fetch data with caching to avoid repeated requests"""
        cache_file = os.path.join(CACHE_DIR, f"{cache_name}.json")
        
        # Try cache first
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                print(f"📦 Loading from cache: {cache_name}")
                return json.load(f)
        
        try:
            print(f"🌐 Fetching: {url}")
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            # Save to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return data
        except requests.exceptions.Timeout:
            print(f"⏱️  Timeout for {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"🌐 Network error for {url}: {e}")
            return None
    
    # ===== BOOK IMPORT =====
    def import_books_simple(self):
        """Import basic book structure manually (since API times out)"""
        print("📚 Importing basic book structure...")
        
        books_to_add = [
            {
                'code': 'bukhari',
                'name_en': 'Sahih al-Bukhari',
                'name_ar': 'صحيح البخاري',
                'total_hadith': 7563
            },
            {
                'code': 'muslim',
                'name_en': 'Sahih Muslim',
                'name_ar': 'صحيح مسلم',
                'total_hadith': 7563
            },
            {
                'code': 'abudawud',
                'name_en': 'Sunan Abu Dawud',
                'name_ar': 'سنن أبي داود',
                'total_hadith': 5274
            },
            {
                'code': 'tirmidhi',
                'name_en': 'Sunan al-Tirmidhi',
                'name_ar': 'سنن الترمذي',
                'total_hadith': 3956
            },
            {
                'code': 'nasai',
                'name_en': 'Sunan al-Nasa\'i',
                'name_ar': 'سنن النسائي',
                'total_hadith': 5761
            },
            {
                'code': 'ibnmajah',
                'name_en': 'Sunan Ibn Majah',
                'name_ar': 'سنن ابن ماجه',
                'total_hadith': 4341
            },
            {
                'code': 'malik',
                'name_en': 'Muwatta Malik',
                'name_ar': 'موطأ مالك',
                'total_hadith': 1854
            }
        ]
        
        for i, book_info in enumerate(books_to_add, 1):
            # Check if book exists
            self.execute_query(
                "SELECT id FROM books WHERE code = %s",
                (book_info['code'],)
            )
            existing = self.cursor.fetchone()
            
            if not existing:
                slug = book_info['code']
                self.execute_query("""
                    INSERT INTO books (code, name_en, name_ar, total_hadith, slug)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    book_info['code'],
                    book_info['name_en'],
                    book_info['name_ar'],
                    book_info['total_hadith'],
                    slug
                ), commit=True)
                
                book_id = self.cursor.lastrowid
                
                # Add English localization
                self.execute_query("""
                    INSERT INTO books_localizations (book_id, localization_id, localization_code, name, slug)
                    VALUES (%s, %s, %s, %s, %s)
                """, (book_id, i, 'en', book_info['name_en'], f"{slug}-en"), commit=True)
                
                # Add Arabic localization
                self.execute_query("""
                    INSERT INTO books_localizations (book_id, localization_id, localization_code, name, slug)
                    VALUES (%s, %s, %s, %s, %s)
                """, (book_id, i + 100, 'ar', book_info['name_ar'], f"{slug}-ar"), commit=True)
                
                print(f"  ✅ Added book: {book_info['name_en']}")
        
        print("✅ Basic books imported successfully")
    
    # ===== CATEGORY IMPORT =====
    def import_categories_fixed(self):
        """Import categories with fixed subcategory handling"""
        print("📁 Importing categories from HadeethEnc...")
        
        try:
            # Get root categories
            root_categories = self.fetch_with_cache(
                f"{HADEETHENC_API}/categories/roots/?language=en",
                "hadeethenc_root_categories"
            )
            
            if not root_categories:
                print("⚠️  Could not fetch categories from HadeethEnc, using default categories")
                self.create_default_categories()
                return
            
            for cat in root_categories:
                if isinstance(cat, dict):
                    self.insert_category(cat, None)
                else:
                    print(f"⚠️  Invalid category format: {cat}")
            
            print("✅ Categories imported successfully")
            
        except Exception as e:
            print(f"❌ Error importing categories: {e}")
            traceback.print_exc()
    
    def insert_category(self, category_data, parent_id):
        """Insert a single category"""
        try:
            # Check if category already exists by title
            self.execute_query(
                "SELECT id FROM categories WHERE name_en = %s",
                (category_data.get('title', ''),)
            )
            existing = self.cursor.fetchone()
            
            if existing:
                category_id = existing['id']
                print(f"  ⚠️ Category already exists: {category_data.get('title')}")
                return category_id
            
            # Insert new category
            slug = f"category-{category_data.get('id', 'unknown')}"
            self.execute_query("""
                INSERT INTO categories (name_en, name_ar, slug, parent_id)
                VALUES (%s, %s, %s, %s)
            """, (
                category_data.get('title', ''),
                None,
                slug,
                parent_id
            ), commit=True)
            
            category_id = self.cursor.lastrowid
            
            # Add localization
            self.execute_query("""
                INSERT INTO category_localizations (category_id, localization_code, name, slug)
                VALUES (%s, %s, %s, %s)
            """, (category_id, 'en', category_data.get('title', ''), slug), commit=True)
            
            print(f"  ✅ Added category: {category_data.get('title')}")
            
            # Try to get subcategories
            cat_id = category_data.get('id')
            if cat_id:
                try:
                    subcategories = self.fetch_with_cache(
                        f"{HADEETHENC_API}/categories/{cat_id}/children/?language=en",
                        f"hadeethenc_subcategories_{cat_id}"
                    )
                    
                    if subcategories and isinstance(subcategories, list):
                        for subcat in subcategories:
                            if isinstance(subcat, dict):
                                self.insert_category(subcat, category_id)
                            else:
                                print(f"    ⚠️ Invalid subcategory format: {subcat}")
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    print(f"    ⚠️ Could not fetch subcategories: {e}")
            
            return category_id
            
        except Exception as e:
            print(f"❌ Error inserting category: {e}")
            return None
    
    def create_default_categories(self):
        """Create default categories if API fails"""
        default_categories = [
            {'id': 1, 'title': 'The Noble Qur\'an and Qur\'anic Sciences'},
            {'id': 2, 'title': 'The Hadith and Hadith Sciences'},
            {'id': 3, 'title': 'The Creed'},
            {'id': 4, 'title': 'Jurisprudence and Juristic Principles'},
            {'id': 5, 'title': 'Virtues and Manners'},
            {'id': 6, 'title': 'Da\'wah and Hisbah'},
            {'id': 7, 'title': 'Seerah and History'},
        ]
        
        for cat in default_categories:
            self.insert_category(cat, None)
    
    # ===== CHAPTER IMPORT =====
    def import_chapters_manual(self, book_id, book_code):
        """Import chapters manually based on known chapter structures"""
        print(f"  📑 Importing chapters for {book_code}...")
        
        # Known chapter structures for popular hadith books
        chapter_structures = {
            'bukhari': [
                "Revelation",
                "Belief",
                "Knowledge",
                "Ablution",
                "Bathing",
                "Menstruation",
                "Tayammum",
                "Prayer",
                "Times of Prayers",
                "Call to Prayer",
                "Friday Prayer",
                "Fear Prayer",
                "The Two Festivals",
                "Witr Prayer",
                "Tahajjud",
                "Supererogatory Prayer",
                "Rain Prayer",
                "Eclipse",
                "Funerals",
                "Zakat",
                "Fasting",
                "Hajj",
                "Jihad",
                "Marriage",
                "Divorce",
                "Business",
                "Wills",
                "Vows",
                "Oaths",
                "Judgements",
                "Gifts",
                "Reconciliation",
                "Lost Things",
                "Oppressions",
                "Partnership",
                "Mortgaging",
                "Manumission",
                "Sales",
                "Borrowing",
                "Agriculture",
                "Drinks",
                "Patients",
                "Medicine",
                "Dress",
                "Good Manners",
                "Asking Permission",
                "Invocations",
                "Heart-Melting Narrations",
                "Oneness of Allah",
                "Quran Tafsir",
                "Marriage of Prophet",
                "Virtues of Prophet",
                "Companions of Prophet",
                "Virtues of Ansar",
                "Military Expeditions",
                "Prophets",
                "Virtues of Quran",
                "Wedlock",
                "Divorce",
                "Food",
                "Sacrifice",
                "Drinks",
                "Patients",
                "Medicine",
                "Dress",
                "Good Manners",
                "Asking Permission",
                "Invocation",
                "Heart-Melting Narrations",
                "Oneness of Allah",
                "Tafsir of Quran",
                "Prophet's Marriage",
                "Virtues of Prophet",
                "Companions of Prophet",
                "Virtues of Ansar",
                "Military Expeditions",
                "Prophets",
                "Virtues of Quran"
            ],
            'abudawud': [
                "Purification",
                "Prayer",
                "Zakat",
                "Fasting",
                "Hajj",
                "Marriage",
                "Divorce",
                "Jihad",
                "Sacrifices",
                "Hunting",
                "Food",
                "Drinks",
                "Medicine",
                "Oaths and Vows",
                "Judgements",
                "Knowledge",
                "Good Manners",
                "Battles",
                "Wills",
                "Funerals"
            ],
            'muslim': [
                "Faith",
                "Purification",
                "Menstruation",
                "Prayer",
                "Zakat",
                "Fasting",
                "Hajj",
                "Marriage",
                "Divorce",
                "Business",
                "Inheritance",
                "Wills",
                "Vows",
                "Oaths",
                "Judgements",
                "Jihad",
                "Government",
                "Hunting",
                "Sacrifices",
                "Food",
                "Drinks",
                "Clothing",
                "Good Manners",
                "Greetings",
                "Visiting the Sick",
                "Funerals",
                "Destiny",
                "Knowledge",
                "Remembrance of Allah",
                "Heart-Melting Traditions",
                "Repentance",
                "Description of Paradise",
                "Trials and Portents",
                "Zuhd",
                "Tafsir",
                "Virtues of Companions"
            ]
        }
        
        chapters = chapter_structures.get(book_code, [])
        
        if not chapters:
            # Generic chapters if not found
            chapters = [f"Chapter {i}" for i in range(1, 51)]
        
        for i, chapter_name in enumerate(chapters, 1):
            # Check if chapter exists
            self.execute_query(
                "SELECT id FROM chapters WHERE book_id = %s AND chapter_no = %s",
                (book_id, i)
            )
            existing = self.cursor.fetchone()
            
            if not existing:
                slug = f"{book_code}-chapter-{i}"
                self.execute_query("""
                    INSERT INTO chapters (book_id, chapter_no, name_en, name_ar, total_hadith, slug)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    book_id,
                    i,
                    chapter_name,
                    chapter_name,  # Same for Arabic initially
                    0,
                    slug
                ), commit=True)
                
                chapter_id = self.cursor.lastrowid
                
                # Add localizations
                self.execute_query("""
                    INSERT INTO chapters_localizations (chapter_id, localization_id, localization_code, name, slug)
                    VALUES (%s, %s, %s, %s, %s)
                """, (chapter_id, i, 'en', chapter_name, f"{slug}-en"), commit=True)
                
                self.execute_query("""
                    INSERT INTO chapters_localizations (chapter_id, localization_id, localization_code, name, slug)
                    VALUES (%s, %s, %s, %s, %s)
                """, (chapter_id, i + 1000, 'ar', chapter_name, f"{slug}-ar"), commit=True)
                
                print(f"    ✅ Chapter {i}: {chapter_name}")
    
    # ===== HADITH IMPORT FROM LOCAL JSON =====
    def import_hadiths_from_local_data(self):
        """Import hadiths from local JSON data files"""
        print("\n📝 Importing hadiths from local data...")
        
        # Define the path to your local JSON data
        local_data_path = "../../hadith-vn/data"  # Adjust this path
        
        try:
            # Load books data
            with open(os.path.join(local_data_path, "books.json"), 'r', encoding='utf-8') as f:
                books_data = json.load(f)
            
            # Load hadiths data
            with open(os.path.join(local_data_path, "hadiths.json"), 'r', encoding='utf-8') as f:
                hadiths_data = json.load(f)
            
            # Load categories data
            with open(os.path.join(local_data_path, "categories.json"), 'r', encoding='utf-8') as f:
                categories_data = json.load(f)
            
            total_hadiths = 0
            
            # Process hadiths from books structure
            for book_key, chapters in hadiths_data.items():
                if book_key == 'categories':
                    continue  # Skip categories section
                
                book_id = int(book_key)
                print(f"\n📖 Processing book ID: {book_id}")
                
                for chapter_key, hadiths in chapters.items():
                    chapter_id = int(chapter_key)
                    
                    for hadith in hadiths:
                        try:
                            # Insert hadith
                            self.execute_query("""
                                INSERT INTO hadiths (book_id, chapter_id, hadith_number, arabic_text, grade)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                book_id,
                                chapter_id,
                                hadith.get('hadith_number', 0),
                                hadith.get('hadeeth', hadith.get('arabic_text', '')),
                                hadith.get('grade', '')
                            ), commit=True)
                            
                            hadith_id = self.cursor.lastrowid
                            total_hadiths += 1
                            
                            # Import translations
                            translations = hadith.get('translations', {})
                            for lang_code, translation_text in translations.items():
                                if translation_text:
                                    self.execute_query("""
                                        INSERT INTO hadith_translations (hadith_id, localization_id, localization_code, translation_text)
                                        VALUES (%s, %s, %s, %s)
                                    """, (
                                        hadith_id,
                                        self.get_localization_id(lang_code),
                                        lang_code,
                                        translation_text
                                    ), commit=True)
                            
                            # Import additional details
                            if hadith.get('explanation') or hadith.get('hints') or hadith.get('references'):
                                self.execute_query("""
                                    INSERT INTO hadith_details (hadith_id, explanation_en, hints_en, references_en)
                                    VALUES (%s, %s, %s, %s)
                                """, (
                                    hadith_id,
                                    hadith.get('explanation', ''),
                                    json.dumps(hadith.get('hints', []), ensure_ascii=False),
                                    json.dumps(hadith.get('references', []), ensure_ascii=False)
                                ), commit=True)
                            
                            # Associate with categories
                            category_id = hadith.get('category_id')
                            if category_id:
                                self.execute_query("""
                                    INSERT IGNORE INTO hadith_category (hadith_id, category_id)
                                    VALUES (%s, %s)
                                """, (hadith_id, category_id), commit=True)
                        
                        except Exception as e:
                            print(f"    ⚠️ Error importing hadith: {e}")
                            continue
            
            # Process hadiths from categories structure
            if 'categories' in hadiths_data:
                for category_id_str, hadiths in hadiths_data['categories'].items():
                    category_id = int(category_id_str)
                    
                    for hadith in hadiths:
                        try:
                            # Insert hadith
                            self.execute_query("""
                                INSERT INTO hadiths (book_id, chapter_id, hadith_number, arabic_text, grade)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                hadith.get('book_id', 1),
                                hadith.get('chapter_id', 1),
                                hadith.get('hadith_number', 0),
                                hadith.get('hadeeth', hadith.get('arabic_text', '')),
                                hadith.get('grade', '')
                            ), commit=True)
                            
                            hadith_id = self.cursor.lastrowid
                            total_hadiths += 1
                            
                            # Associate with category
                            self.execute_query("""
                                INSERT IGNORE INTO hadith_category (hadith_id, category_id)
                                VALUES (%s, %s)
                            """, (hadith_id, category_id), commit=True)
                            
                            # Import translations
                            translations = hadith.get('translations', {})
                            for lang_code, translation_text in translations.items():
                                if translation_text:
                                    self.execute_query("""
                                        INSERT INTO hadith_translations (hadith_id, localization_id, localization_code, translation_text)
                                        VALUES (%s, %s, %s, %s)
                                    """, (
                                        hadith_id,
                                        self.get_localization_id(lang_code),
                                        lang_code,
                                        translation_text
                                    ), commit=True)
                        
                        except Exception as e:
                            print(f"    ⚠️ Error importing category hadith: {e}")
                            continue
            
            print(f"\n✅ Imported {total_hadiths} hadiths from local data")
            
        except FileNotFoundError as e:
            print(f"❌ Local data files not found: {e}")
            print("Please make sure the path to your JSON data files is correct.")
        except Exception as e:
            print(f"❌ Error importing from local data: {e}")
            traceback.print_exc()
    
    def get_localization_id(self, lang_code):
        """Get localization ID for language code"""
        lang_ids = {
            'ar': 1, 'en': 2, 'bn': 3, 'ur': 4, 'tr': 5,
            'fr': 6, 'es': 7, 'id': 8, 'ru': 9, 'fa': 10,
            'vi': 11, 'hi': 12, 'si': 13, 'tl': 14, 'zh': 15
        }
        return lang_ids.get(lang_code, 2)  # Default to English
    
    # ===== ENHANCE WITH HADEETHENC DETAILS =====
    def enhance_with_hadeethenc(self, limit=100):
        """Enhance hadiths with details from HadeethEnc API"""
        print(f"\n🔍 Enhancing hadiths with HadeethEnc details (limit: {limit})...")
        
        # Get hadiths that need enhancement
        self.execute_query("SELECT id FROM hadiths ORDER BY id LIMIT %s", (limit,))
        hadiths = self.cursor.fetchall()
        
        enhanced_count = 0
        
        for i, hadith in enumerate(hadiths, 1):
            try:
                # Get hadith details from HadeethEnc
                data = self.fetch_with_cache(
                    f"{HADEETHENC_API}/hadeeths/one/?id={hadith['id']}&language=ar",
                    f"hadeeth_{hadith['id']}_ar"
                )
                
                if data and 'hadith' in data:
                    hadith_data = data['hadith']
                    
                    # Create or update hadith_details
                    self.execute_query("""
                        INSERT INTO hadith_details (hadith_id, explanation_ar, hints_ar, references_ar, word_meanings_ar)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        explanation_ar = VALUES(explanation_ar),
                        hints_ar = VALUES(hints_ar),
                        references_ar = VALUES(references_ar),
                        word_meanings_ar = VALUES(word_meanings_ar)
                    """, (
                        hadith['id'],
                        hadith_data.get('explanation', ''),
                        json.dumps(hadith_data.get('hints', []), ensure_ascii=False),
                        json.dumps(hadith_data.get('references', []), ensure_ascii=False),
                        json.dumps(hadith_data.get('words_meanings', []), ensure_ascii=False)
                    ), commit=True)
                    
                    enhanced_count += 1
                
                # Get English details
                eng_data = self.fetch_with_cache(
                    f"{HADEETHENC_API}/hadeeths/one/?id={hadith['id']}&language=en",
                    f"hadeeth_{hadith['id']}_en"
                )
                
                if eng_data and 'hadith' in eng_data:
                    eng_hadith = eng_data['hadith']
                    
                    # Update English details
                    self.execute_query("""
                        UPDATE hadith_details 
                        SET explanation_en = %s,
                            hints_en = %s,
                            references_en = %s,
                            word_meanings_en = %s
                        WHERE hadith_id = %s
                    """, (
                        eng_hadith.get('explanation', ''),
                        json.dumps(eng_hadith.get('hints', []), ensure_ascii=False),
                        json.dumps(eng_hadith.get('references', []), ensure_ascii=False),
                        json.dumps(eng_hadith.get('words_meanings', []), ensure_ascii=False),
                        hadith['id']
                    ), commit=True)
                
                if i % 10 == 0:
                    print(f"  ✅ Enhanced {i}/{len(hadiths)} hadiths")
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"  ⚠️ Error enhancing hadith {hadith['id']}: {e}")
                continue
        
        print(f"✅ Enhanced {enhanced_count} hadiths with HadeethEnc details")
    
    # ===== UPDATE STATISTICS =====
    def update_statistics(self):
        """Update book and chapter statistics"""
        print("\n📊 Updating statistics...")
        
        # Update chapter statistics
        self.execute_query("""
            UPDATE chapters c
            SET total_hadith = (
                SELECT COUNT(*) 
                FROM hadiths h 
                WHERE h.chapter_id = c.id
            )
        """, commit=True)
        
        # Update book statistics
        self.execute_query("""
            UPDATE books b
            SET total_hadith = (
                SELECT COUNT(*) 
                FROM hadiths h 
                WHERE h.book_id = b.id
            )
        """, commit=True)
        
        print("✅ Statistics updated")
    
    # ===== MAIN IMPORT PROCESS =====
    def run_basic_import(self):
        """Run basic import process"""
        print("🚀 Starting Basic Import Process")
        print("=" * 50)
        
        try:
            # Step 1: Import basic books
            self.import_books_simple()
            
            # Step 2: Import categories
            self.import_categories_fixed()
            
            # Step 3: Import chapters for each book
            self.execute_query("SELECT id, code FROM books")
            books = self.cursor.fetchall()
            
            for book in books:
                self.import_chapters_manual(book['id'], book['code'])
            
            # Step 4: Import hadiths from local JSON data
            self.import_hadiths_from_local_data()
            
            # Step 5: Update statistics
            self.update_statistics()
            
            # Step 6: Show final statistics
            self.show_final_statistics()
            
        except KeyboardInterrupt:
            print("\n\n⏹️ Import interrupted by user")
        except Exception as e:
            print(f"\n❌ Import failed: {e}")
            traceback.print_exc()
        finally:
            self.close_db()
    
    def run_enhanced_import(self):
        """Run enhanced import process with HadeethEnc details"""
        print("🚀 Starting Enhanced Import Process")
        print("=" * 50)
        
        try:
            # Run basic import first
            self.run_basic_import()
            
            # Reconnect for enhancement
            self.connect_db()
            
            # Enhance with HadeethEnc details
            self.enhance_with_hadeethenc(limit=200)  # Limit to 200 for testing
            
        except KeyboardInterrupt:
            print("\n\n⏹️ Enhancement interrupted by user")
        except Exception as e:
            print(f"\n❌ Enhancement failed: {e}")
            traceback.print_exc()
        finally:
            self.close_db()
    
    def run_translation_update(self):
        """Update translations only"""
        print("🔤 Starting Translation Update")
        print("=" * 50)
        
        try:
            self.connect_db()
            
            # This would update translations from various sources
            # For now, just show a message
            print("Translation update functionality to be implemented")
            print("You can manually update translations by:")
            print("1. Running the basic import again")
            print("2. Using the HadeethEnc API to fetch new translations")
            
        except Exception as e:
            print(f"\n❌ Update failed: {e}")
            traceback.print_exc()
        finally:
            self.close_db()
    
    def show_final_statistics(self):
        """Show final import statistics"""
        print(f"\n{'='*50}")
        print("🎉 Import Complete!")
        print(f"{'='*50}")
        
        # Get final counts
        queries = [
            ("📚 Books", "SELECT COUNT(*) as count FROM books"),
            ("📑 Chapters", "SELECT COUNT(*) as count FROM chapters"),
            ("📝 Hadiths", "SELECT COUNT(*) as count FROM hadiths"),
            ("🔤 Translations", "SELECT COUNT(*) as count FROM hadith_translations"),
            ("📁 Categories", "SELECT COUNT(*) as count FROM categories"),
            ("💡 Details", "SELECT COUNT(*) as count FROM hadith_details"),
            ("🌐 Languages", "SELECT COUNT(DISTINCT localization_code) as count FROM hadith_translations")
        ]
        
        for label, query in queries:
            self.execute_query(query)
            result = self.cursor.fetchone()
            print(f"{label}: {result['count'] if result else 0}")
        
        print(f"{'='*50}")

# ===== RUN SCRIPT =====
if __name__ == "__main__":
    print("🕌 Improved Hadith Database Importer")
    print("=" * 50)
    
    # Create cache directory
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Choose import mode
    print("\nSelect import mode:")
    print("1. Basic import (structure + local data)")
    print("2. Enhanced import (with HadeethEnc details)")
    print("3. Update translations only")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    importer = ImprovedHadithImporter()
    
    if choice == "1":
        importer.run_basic_import()
    elif choice == "2":
        importer.run_enhanced_import()
    elif choice == "3":
        importer.run_translation_update()
    else:
        print("❌ Invalid choice")