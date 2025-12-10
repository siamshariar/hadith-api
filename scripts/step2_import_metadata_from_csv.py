"""
Step 2: Import metadata from CSV files into database - FIXED VERSION
"""

import csv
import sys
import os
from utils import get_db_connection, batch_insert, CSV_OUTPUT_DIR
from config import DB_CONFIG


def import_csv_to_table(cursor, csv_filename: str, table: str, 
                        duplicate_check_cols: list = None):
    """
    Import CSV file into database table - FIXED VERSION
    """
    filepath = os.path.join(CSV_OUTPUT_DIR, csv_filename)
    
    if not os.path.exists(filepath):
        print(f"[ERROR] CSV file not found: {filepath}")
        return
    
    print(f"\n[IMPORT] Importing {csv_filename} into {table}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Skip header row
        rows = [tuple(row) for row in reader]
    
    if not rows:
        print(f"⚠️ No data found in {csv_filename}")
        return
    
    # Remove 'id' column if present (auto-increment)
    if 'id' in headers:
        id_index = headers.index('id')
        headers = [h for i, h in enumerate(headers) if i != id_index]
        rows = [tuple(v for i, v in enumerate(row) if i != id_index) for row in rows]
    
    # For categories table, we need special handling for parent_id
    if table == 'categories':
        # Convert empty strings to None for parent_id
        parent_id_index = headers.index('parent_id') if 'parent_id' in headers else -1
        if parent_id_index >= 0:
            new_rows = []
            for row in rows:
                row_list = list(row)
                if row_list[parent_id_index] == '':
                    row_list[parent_id_index] = None
                new_rows.append(tuple(row_list))
            rows = new_rows
    
    batch_insert(
        cursor, 
        table, 
        headers, 
        rows, 
        check_duplicates=True,
        duplicate_check_cols=duplicate_check_cols
    )


def main():
    """Main function to import all metadata from CSV - FIXED VERSION"""
    print("=" * 60)
    print("STEP 2: Import Metadata from CSV Files - FIXED")
    print("=" * 60)
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Import in order (respecting foreign key constraints)
        print("\n[SYNC] Importing in correct order to maintain relationships...")
        
        # 1. Books first (no dependencies)
        import_csv_to_table(
            cursor, 
            'books.csv', 
            'books',
            duplicate_check_cols=['code']
        )
        
        # 2. Books localizations (depends on books)
        import_csv_to_table(
            cursor, 
            'books_localizations.csv', 
            'books_localizations',
            duplicate_check_cols=['book_id', 'localization_code']
        )
        
        # 3. Categories (parent-child, special handling needed)
        print("\n[DIR] Importing categories (with parent-child relationships)...")
        import_csv_to_table(
            cursor, 
            'categories.csv', 
            'categories',
            duplicate_check_cols=['id']  # Use id for categories
        )
        
        # 4. Category localizations (depends on categories)
        import_csv_to_table(
            cursor, 
            'category_localizations.csv', 
            'category_localizations',
            duplicate_check_cols=['category_id', 'localization_code']
        )
        
        # 5. Chapters (depends on books)
        import_csv_to_table(
            cursor, 
            'chapters.csv', 
            'chapters',
            duplicate_check_cols=['book_id', 'chapter_no']
        )
        
        # 6. Chapters localizations (depends on chapters)
        import_csv_to_table(
            cursor, 
            'chapters_localizations.csv', 
            'chapters_localizations',
            duplicate_check_cols=['chapter_id', 'localization_code']
        )
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("[OK] All metadata imported successfully!")
        print("=" * 60)
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM books")
        books_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chapters")
        chapters_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM categories")
        categories_count = cursor.fetchone()[0]
        
        print(f"\n[STATS] IMPORT SUMMARY:")
        print(f"  [BOOKS] Books: {books_count}")
        print(f"  [CHAPTERS] Chapters: {chapters_count}")
        print(f"  [CATEGORIES] Categories: {categories_count}")
        
        print("\n[NEXT] Next steps:")
        print("1. Verify data in database")
        print("2. Run: python step4_import_hadiths_fawaz.py")
        print("   (This will import actual hadith texts and translations)")
        print("=" * 60)
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n[ERROR] Error importing metadata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    main()