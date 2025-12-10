"""
Step 4: Import hadiths and translations from Fawaz Hadith API - MYSQL VERSION
This script properly imports hadiths with correct API handling and database mapping
"""

import sys
import time
import mysql.connector
import argparse
from utils import get_db_connection, fetch_api_data, clean_text
from config import FAWAZ_HADITH_API_EDITIONS, BOOK_CODE_MAP, LOCALIZATION_MAP


def get_chapter_mapping(cursor, book_id: int, chapter_no: int) -> int:
    """
    Get or create chapter mapping for a book
    """
    cursor.execute("""
        SELECT id FROM chapters 
        WHERE book_id = %s AND chapter_no = %s
        LIMIT 1
    """, (book_id, chapter_no))
    
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # If chapter doesn't exist, create it
    cursor.execute("""
        INSERT INTO chapters 
        (book_id, chapter_no, name_en, name_ar, total_hadith, slug, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
    """, (book_id, chapter_no, f"Chapter {chapter_no}", "", 0, f"chapter-{chapter_no}"))
    
    return cursor.lastrowid


def import_fawaz_hadiths_fixed(cursor, edition_name: str, book_id: int, lang_code: str, max_hadiths: int = 5000, skip_if_exists: bool = False):
    """
    Import hadiths from Fawaz API - FIXED VERSION
    skip_if_exists: if True, skip languages that already have translations for this hadith
    """
    print(f"[IMPORT] Importing {edition_name} ({lang_code})...")
    if skip_if_exists:
        print(f"   (Will skip if HadeethEnc translations exist for this language)")
    
    imported = 0
    skipped = 0
    errors = 0
    consecutive_failures = 0
    max_consecutive_failures = 15
    
    for hadith_num in range(1, max_hadiths + 1):
        if consecutive_failures >= max_consecutive_failures:
            print(f"  ⏹️ Stopped after {consecutive_failures} consecutive failures")
            break
        
        # Construct URL - try both .json and .min.json
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
            consecutive_failures += 1
            if hadith_num <= 3:  # Debug first few failures
                print(f"  [ERROR] No data for hadith {hadith_num} (URL tried: {urls[0]})")
            continue
        
        consecutive_failures = 0
        
        consecutive_failures = 0
        
        try:
            # Extract hadith information - Fawaz API structure: {'metadata': {...}, 'hadiths': [...]}
            if 'hadiths' in hadith_data and isinstance(hadith_data['hadiths'], list) and hadith_data['hadiths']:
                hadith_info = hadith_data['hadiths'][0]  # Take first hadith from array
            else:
                hadith_info = hadith_data.get('hadith', hadith_data)
            
            # Get text based on language
            
            # Get text based on language
            if lang_code == 'ar':
                text = hadith_info.get('text', '') or hadith_info.get('arabic', '')
            else:
                text = hadith_info.get('text', '') or hadith_info.get('translation', '')
            
            text = clean_text(text)
            
            if not text or len(text.strip()) < 10:  # Minimum text length check
                if hadith_num <= 5:  # Debug first few
                    print(f"  [WARN] Text too short for hadith {hadith_num}: '{text[:50]}...' (len={len(text.strip())})")
                skipped += 1
                continue
            
            # Get chapter information
            chapter_no = hadith_info.get('chapterNo', 
                          hadith_info.get('chapterno', 
                          hadith_info.get('chapter', 1)))
            
            if isinstance(chapter_no, str):
                try:
                    chapter_no = int(chapter_no)
                except:
                    chapter_no = 1
            
            # Get chapter ID
            chapter_id = get_chapter_mapping(cursor, book_id, chapter_no)
            
            hadith_number = str(hadith_info.get('hadithNumber', 
                              hadith_info.get('hadithnumber', 
                              hadith_num)))
            
            # For Arabic texts - insert as main hadith
            if lang_code == 'ar':
                # Check if hadith already exists
                cursor.execute("""
                    SELECT id FROM hadiths 
                    WHERE book_id = %s AND hadith_number = %s
                """, (book_id, hadith_number))
                
                if cursor.fetchone():
                    skipped += 1
                    continue
                
                # Get grade if available - Fawaz API uses 'grades' (plural)
                raw_grade = hadith_info.get('grades', 
                         hadith_info.get('grade', 
                         hadith_info.get('classification', 
                         None)))

                # Normalize grade into a string. Handle lists of dicts, lists of strings,
                # single dicts, and simple strings. Collect distinct grade verdicts
                # when multiple scholars are present and join them with ' | '.
                grade = None
                try:
                    if isinstance(raw_grade, list):
                        grades_found = []
                        for g in raw_grade:
                            if isinstance(g, dict):
                                val = g.get('grade') or g.get('name')
                                if val:
                                    grades_found.append(str(val).strip())
                            elif isinstance(g, str):
                                if g.strip():
                                    grades_found.append(g.strip())
                        # deduplicate while preserving order
                        seen = set()
                        grades_unique = []
                        for v in grades_found:
                            if v not in seen:
                                seen.add(v)
                                grades_unique.append(v)
                        grade = ' | '.join(grades_unique) if grades_unique else None
                    elif isinstance(raw_grade, dict):
                        grade = raw_grade.get('grade') or raw_grade.get('name')
                    elif isinstance(raw_grade, str):
                        grade = raw_grade.strip() or None
                except Exception:
                    grade = str(raw_grade) if raw_grade is not None else None

                # Ensure grade is a string or None
                if grade is not None and not isinstance(grade, str):
                    grade = str(grade)
                
                # Insert main hadith
                cursor.execute("""
                    INSERT INTO hadiths 
                    (book_id, chapter_id, hadith_number, arabic_text, grade, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                """, (book_id, chapter_id, hadith_number, text, grade))
                
                imported += 1
                
            else:
                # For translations - find the corresponding Arabic hadith
                cursor.execute("""
                    SELECT id FROM hadiths 
                    WHERE book_id = %s AND hadith_number = %s
                """, (book_id, hadith_number))
                
                result = cursor.fetchone()
                if not result:
                    # If Arabic hadith doesn't exist yet, skip for now
                    skipped += 1
                    continue
                
                hadith_id = result[0]

                # If skip_if_exists is True and this language already has a translation, skip it
                if skip_if_exists:
                    cursor.execute("""
                        SELECT id FROM hadith_translations 
                        WHERE hadith_id = %s AND localization_code = %s
                    """, (hadith_id, lang_code))
                    if cursor.fetchone():
                        skipped += 1
                        continue

                # If Arabic hadith has no grade, try to extract grade from this
                # edition (some translations include 'grades') and update parent.
                cursor.execute("SELECT grade FROM hadiths WHERE id = %s", (hadith_id,))
                existing_grade = cursor.fetchone()[0]
                if not existing_grade:
                    trans_raw_grade = hadith_info.get('grades', hadith_info.get('grade', None))
                    trans_grade = None
                    try:
                        if isinstance(trans_raw_grade, list):
                            grades_found = []
                            for g in trans_raw_grade:
                                if isinstance(g, dict):
                                    val = g.get('grade') or g.get('name')
                                    if val:
                                        grades_found.append(str(val).strip())
                                elif isinstance(g, str):
                                    if g.strip():
                                        grades_found.append(g.strip())
                            seen = set()
                            grades_unique = []
                            for v in grades_found:
                                if v not in seen:
                                    seen.add(v)
                                    grades_unique.append(v)
                            if grades_unique:
                                trans_grade = ' | '.join(grades_unique)
                        elif isinstance(trans_raw_grade, dict):
                            trans_grade = trans_raw_grade.get('grade') or trans_raw_grade.get('name')
                        elif isinstance(trans_raw_grade, str):
                            trans_grade = trans_raw_grade.strip() or None
                    except Exception:
                        trans_grade = str(trans_raw_grade) if trans_raw_grade is not None else None

                    if trans_grade:
                        cursor.execute("UPDATE hadiths SET grade = %s WHERE id = %s", (trans_grade, hadith_id))

                # Check if translation already exists
                cursor.execute("""
                    SELECT id FROM hadith_translations 
                    WHERE hadith_id = %s AND localization_code = %s
                """, (hadith_id, lang_code))
                
                if cursor.fetchone():
                    skipped += 1
                    continue
                
                # Insert translation
                localization_id = LOCALIZATION_MAP.get(lang_code, {}).get('id', 1)
                
                cursor.execute("""
                    INSERT INTO hadith_translations 
                    (hadith_id, localization_id, localization_code, translation_text, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                """, (hadith_id, localization_id, lang_code, text))
                
                imported += 1
            
            # Progress indicator
            if imported > 0 and (imported % 100 == 0 or hadith_num % 500 == 0):
                print(f"  [STATS] Progress: {hadith_num} checked, {imported} imported...")
                
        except Exception as e:
            errors += 1
            print(f"  [WARN] Error processing hadith {hadith_num}: {e}")
            continue
    
    print(f"  [OK] Completed: {imported} imported, {skipped} skipped, {errors} errors")
    return imported


def import_all_fawaz_hadiths_fixed(max_hadiths: int = 5000, book_filter: list = None, languages: list = ['ar', 'en'], prefer_hadeethenc: bool = False):
    """Main import function - FIXED VERSION
    prefer_hadeethenc: if True, skip languages that already have translations from HadeethEnc
    """
    print("=" * 70)
    print("STEP 4 FIXED: Import Hadiths from Fawaz API - PROPERLY WORKING")
    if prefer_hadeethenc:
        print("MODE: Prefer HadeethEnc - skipping already-translated languages")
    print("=" * 70)
    
    conn = None
    total_imported = 0
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get books from database
        cursor.execute("SELECT id, code FROM books")
        books = {code: book_id for book_id, code in cursor.fetchall()}
        
        for book_code, book_info in BOOK_CODE_MAP.items():
            if book_filter and book_code not in book_filter:
                continue
                
            if book_code not in books:
                print(f"[WARN] Book {book_code} not found in database, skipping...")
                continue
            
            book_id = books[book_code]
            fawaz_arabic = book_info.get('fawaz', '')
            
            if not fawaz_arabic:
                print(f"[WARN] No Fawaz code for {book_code}, skipping...")
                continue
            
            print(f"\n{'='*50}")
            print(f"[BOOK] PROCESSING: {book_info['name_en']}")
            print(f"{'='*50}")
            
            # Import Arabic hadiths first (main texts)
            if 'ar' in languages:
                arabic_imported = import_fawaz_hadiths_fixed(cursor, fawaz_arabic, book_id, 'ar', max_hadiths)
                conn.commit()
                total_imported += arabic_imported
            
            # Import other languages
            for lang in languages:
                if lang == 'ar':
                    continue  # Already imported above
                    
                edition_map = {
                    'en': fawaz_arabic.replace('ara-', 'eng-'),
                    'ur': fawaz_arabic.replace('ara-', 'urd-'),
                    'bn': fawaz_arabic.replace('ara-', 'ben-'),
                    'hi': fawaz_arabic.replace('ara-', 'hin-'),
                    'tr': fawaz_arabic.replace('ara-', 'tur-'),
                    'fa': fawaz_arabic.replace('ara-', 'per-'),
                    'fr': fawaz_arabic.replace('ara-', 'fre-'),
                    'es': fawaz_arabic.replace('ara-', 'spa-'),
                }
                
                if lang in edition_map:
                    lang_imported = import_fawaz_hadiths_fixed(cursor, edition_map[lang], book_id, lang, max_hadiths, skip_if_exists=prefer_hadeethenc)
                    conn.commit()
                    total_imported += lang_imported
                    
                    print(f"[STATS] {book_info['name_en']} - {lang.upper()}: {lang_imported}")
            
            print(f"[STATS] {book_info['name_en']} summary:")
            print(f"   Arabic: {arabic_imported if 'ar' in languages else 0}")
            for lang in languages:
                if lang != 'ar' and lang in locals():
                    print(f"   {lang.upper()}: {locals().get(f'{lang}_imported', 0)}")
        
        print("\n" + "=" * 70)
        print("[SUCCESS] ALL HADITHS IMPORTED SUCCESSFULLY!")
        print("=" * 70)
        print(f"[GROWTH] Total hadiths/translations imported: {total_imported}")
        
        # Show final statistics
        cursor.execute("SELECT COUNT(*) FROM hadiths")
        total_hadiths = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM hadith_translations") 
        total_translations = cursor.fetchone()[0]
        
        print(f"[STATS] Database now has:")
        print(f"   {total_hadiths} hadith texts")
        print(f"   {total_translations} translations")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            cursor.close()
            conn.close()
    
    return True


def main():
    """Main function with command line options"""
    parser = argparse.ArgumentParser(description='Import hadiths from Fawaz API')
    parser.add_argument('--sample', type=int, default=None, 
                       help='Import only first N hadiths per book/chapter for testing (e.g., --sample 100)')
    parser.add_argument('--books', nargs='*', default=None,
                       help='Import only specific books by code (e.g., --books bukhari muslim)')
    parser.add_argument('--languages', nargs='*', default=['ar', 'en'],
                       help='Languages to import (default: ar en)')
    parser.add_argument('--prefer-hadeethenc', action='store_true',
                       help='Skip languages already translated by HadeethEnc (run after HadeethEnc import)')
    
    args = parser.parse_args()
    
    # Determine max hadiths per book/chapter
    max_per_book = args.sample if args.sample else 5000
    
    print("=" * 70)
    if args.sample:
        print(f"SAMPLE IMPORT: First {args.sample} hadiths per book/chapter")
    else:
        print("FULL IMPORT: All hadiths from Fawaz API")
    if args.prefer_hadeethenc:
        print("MODE: Prefer HadeethEnc - skipping languages already translated")
    print("=" * 70)
    
    success = import_all_fawaz_hadiths_fixed(max_hadiths=max_per_book, 
                                           book_filter=args.books,
                                           languages=args.languages,
                                           prefer_hadeethenc=args.prefer_hadeethenc)
    
    if success:
        print("\n[OK] Hadith import completed successfully!")
        if args.sample:
            print(f"[NOTE] This was a SAMPLE run ({args.sample} hadiths per book)")
            print("   Run without --sample to import ALL hadiths")
        else:
            print("[TARGET] Your database now contains complete hadith data!")
    else:
        print("\n[ERROR] Hadith import failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()