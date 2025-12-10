#!/usr/bin/env python3
"""
Import ALL HadeethEnc categories with complete metadata
FIXED VERSION: Imports all 447 categories, properly saves explanation, hints, word_meanings, references
Usage: python step5_import_hadeethenc_complete.py [--test] [--category ID] [--limit N]
"""

import mysql.connector
import requests
import sys
import json
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '123456',
    'database': 'hadith_api_prod'
}

API_BASE = 'https://hadeethenc.com/api/v1'

# All 16 languages
LANGUAGES = {
    'ar': 1, 'en': 2, 'ur': 3, 'bn': 4, 'tr': 5, 'fa': 6, 'fr': 7, 'es': 8,
    'ru': 9, 'id': 10, 'bs': 11, 'zh': 12, 'tl': 13, 'hi': 14, 'vi': 15, 'si': 16, 'ug': 17
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def api_get(endpoint, params=None):
    try:
        response = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return None

def import_category(category_id):
    """Import all hadiths from one category"""
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Get book and chapter
    cursor.execute("SELECT id FROM books WHERE id = 10")
    book_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT id FROM chapters WHERE book_id = %s LIMIT 1", (book_id,))
    chapter_result = cursor.fetchone()
    if chapter_result:
        chapter_id = chapter_result[0]
    else:
        cursor.execute("INSERT INTO chapters (book_id, chapter_number, created_at, updated_at) VALUES (%s, '1', NOW(), NOW())", (book_id,))
        chapter_id = cursor.lastrowid
        conn.commit()
    
    # FIXED: Get category info from full categories list (not just roots - THIS IS CRITICAL!)
    categories_data = api_get('categories/list', {'language': 'en'})
    category_info = next((c for c in categories_data if int(c['id']) == int(category_id)), None)
    
    if not category_info:
        log(f"[ERROR] Category {category_id} not found in API")
        return
    
    # Check if category has hadiths
    hadith_count = int(category_info.get('hadeeths_count', 0))
    if hadith_count == 0:
        log(f"[SKIP] Category {category_id} ({category_info['title']}) has no hadiths (organizational category only)")
        return
    
    category_name = category_info['title']
    total_expected = hadith_count
    
    log(f"\n{'='*80}")
    log(f"Category: {category_name} (ID: {category_id})")
    log(f"Expected hadiths: {total_expected}")
    log(f"{'='*80}\n")
    
    page = 1
    imported = 0
    skipped = 0
    
    while True:
        hadiths_data = api_get('hadeeths/list', {
            'language': 'en',
            'category_id': category_id,
            'page': page,
            'per_page': 50
        })
        
        if not hadiths_data or not hadiths_data.get('data'):
            break
        
        hadith_list = hadiths_data['data']
        log(f"Page {page}: Processing {len(hadith_list)} hadiths...")
        
        for hadith_item in hadith_list:
            hadith_id_api = hadith_item.get('id')
            if not hadith_id_api:
                continue
            
            try:
                # Get Arabic data
                ar_data = api_get('hadeeths/one', {'language': 'ar', 'id': hadith_id_api})
                if not ar_data:
                    continue
                
                arabic_text = ar_data.get('hadeeth', '')
                
                # Check if exists
                cursor.execute("SELECT id FROM hadiths WHERE book_id = %s AND arabic_text = %s", (book_id, arabic_text))
                existing = cursor.fetchone()
                cursor.fetchall()
                
                if existing:
                    skipped += 1
                    continue
                
                # Extract references (try both 'references' and 'reference' keys)
                refs = ar_data.get('references', []) or ar_data.get('reference', [])
                if not refs and 'references_numbered' in ar_data:
                    ref_numbered = ar_data['references_numbered']
                    if isinstance(ref_numbered, dict):
                        refs = [ref_numbered[k] for k in sorted(ref_numbered.keys(), key=lambda x: int(x))]
                
                # Insert hadith
                cursor.execute("""
                    INSERT INTO hadiths (
                        book_id, chapter_id, hadith_number, arabic_text,
                        grade, explanation, hints, word_meanings, `references`,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    book_id, chapter_id, str(imported + 1), arabic_text,
                    ar_data.get('grade', ''),
                    ar_data.get('explanation', ''),
                    json.dumps(ar_data.get('hints', []), ensure_ascii=False) if ar_data.get('hints') else None,
                    json.dumps(ar_data.get('words_meanings', []), ensure_ascii=False) if ar_data.get('words_meanings') else None,
                    json.dumps(refs, ensure_ascii=False) if refs else None
                ))
                
                db_hadith_id = cursor.lastrowid
                
                # Link to category
                cursor.execute("INSERT IGNORE INTO hadith_category (hadith_id, category_id) VALUES (%s, %s)", (db_hadith_id, category_id))
                
                # Import translations
                trans_count = 0
                for lang_code, localization_id in LANGUAGES.items():
                    lang_data = api_get('hadeeths/one', {'language': lang_code, 'id': hadith_id_api})
                    if lang_data and lang_data.get('hadeeth'):
                        # Extract language-specific references
                        lang_refs = lang_data.get('references', []) or lang_data.get('reference', [])
                        if not lang_refs and 'references_numbered' in lang_data:
                            ref_numbered = lang_data['references_numbered']
                            if isinstance(ref_numbered, dict):
                                lang_refs = [ref_numbered[k] for k in sorted(ref_numbered.keys(), key=lambda x: int(x))]
                        
                        cursor.execute("""
                            INSERT INTO hadith_translations (
                                hadith_id, localization_id, localization_code,
                                translation_text, explanation, hints, `references`,
                                created_at, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """, (
                            db_hadith_id, localization_id, lang_code,
                            lang_data.get('hadeeth', ''),
                            lang_data.get('explanation', ''),
                            json.dumps(lang_data.get('hints', []), ensure_ascii=False) if lang_data.get('hints') else None,
                            json.dumps(lang_refs, ensure_ascii=False) if lang_refs else None
                        ))
                        trans_count += 1
                        
                        # Also save to hadith_reference_translations for proper language-wise references
                        if lang_refs:
                            try:
                                cursor.execute("""
                                    INSERT INTO hadith_reference_translations (
                                        hadith_id, localization_code, references_text,
                                        created_at, updated_at
                                    ) VALUES (%s, %s, %s, NOW(), NOW())
                                    ON DUPLICATE KEY UPDATE
                                    references_text = VALUES(references_text),
                                    updated_at = NOW()
                                """, (
                                    db_hadith_id, lang_code,
                                    json.dumps(lang_refs, ensure_ascii=False)
                                ))
                            except:
                                pass  # Skip if already exists
                
                conn.commit()
                imported += 1
                
                if imported % 10 == 0:
                    log(f"  [OK] Imported: {imported}, Skipped: {skipped}, Translations: ~{imported * 16}")
                
            except Exception as e:
                log(f"  [ERROR] Error with hadith {hadith_id_api}: {e}")
                conn.rollback()
        
        if len(hadith_list) < 50:
            break
        page += 1
    
    log(f"\n{'='*80}")
    log(f"[COMPLETE!]")
    log(f"Imported: {imported} new hadiths")
    log(f"Skipped: {skipped} already exist")
    log(f"Total in this category: {imported + skipped}")
    log(f"{'='*80}\n")
    
    conn.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Import HadeethEnc hadiths')
    parser.add_argument('--test', action='store_true', help='Test mode (5 hadiths per category)')
    parser.add_argument('--category', type=int, help='Import specific category ID only')
    parser.add_argument('--limit', type=int, help='Limit hadiths per category')
    args = parser.parse_args()
    
    # Fetch all categories
    log("="*80)
    log("HadeethEnc Complete Import - ALL Categories with Full Metadata")
    log("="*80)
    log("\nFetching all categories from API...")
    
    categories_data = api_get('categories/list', {'language': 'en'})
    if not categories_data:
        log("[ERROR] Could not fetch categories")
        sys.exit(1)
    
    log(f"[OK] Found {len(categories_data)} total categories")
    
    # Filter to categories with hadiths
    categories_with_hadiths = [c for c in categories_data if int(c.get('hadeeths_count', 0)) > 0]
    log(f"[OK] {len(categories_with_hadiths)} categories have hadiths")
    
    total_hadiths = sum(int(c.get('hadeeths_count', 0)) for c in categories_with_hadiths)
    log(f"[OK] Total hadiths available: {total_hadiths}")
    
    # Filter to specific category if requested
    if args.category:
        categories_with_hadiths = [c for c in categories_with_hadiths if int(c['id']) == args.category]
        log(f"[OK] Filtered to category ID: {args.category}")
    
    # Import each category
    total_imported = 0
    for idx, category in enumerate(categories_with_hadiths, 1):
        cat_id = int(category['id'])
        cat_title = category['title']
        cat_count = int(category.get('hadeeths_count', 0))
        
        log(f"\n[{idx}/{len(categories_with_hadiths)}] Processing category: {cat_title} (ID: {cat_id}, {cat_count} hadiths)")
        
        import_category(cat_id)
        
        if args.test and idx >= 1:
            log(f"\n[TEST MODE] Stopping after first category")
            break
    
    log("\n" + "="*80)
    log("IMPORT COMPLETE!")
    log(f"Processed {len(categories_with_hadiths)} categories")
    log("="*80)
