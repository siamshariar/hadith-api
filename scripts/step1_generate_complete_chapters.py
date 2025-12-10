"""
Step 1: Generate Complete Chapter Data Using Predefined Structures
FAST VERSION - Uses predefined chapter structures instead of API scanning
"""

import sys
import os
from utils import create_slug, write_to_csv
from config import BOOK_CODE_MAP, LOCALIZATION_MAP, CSV_OUTPUT_DIR, PREDEFINED_CHAPTERS


def get_book_info():
    """Get book information from predefined data"""
    books_info = {}
    book_id = 1

    for book_code, book_info in BOOK_CODE_MAP.items():
        books_info[book_code] = {
            'id': book_id,
            'code': book_code,
            'name_en': book_info['name_en'],
            'name_ar': book_info['name_ar'],
            'total_hadith': book_info.get('total_hadith', 5000),
            'chapters': book_info.get('chapters', 25)
        }
        book_id += 1

    print(f"[OK] Loaded information for {len(books_info)} books")
    return books_info


def generate_books_csv(books_info):
    """Generate books.csv"""
    print("\n=== Generating Books CSV ===")

    headers = ['id', 'code', 'name_en', 'name_ar', 'total_hadith', 'slug']
    rows = []

    for book_code, book_info in books_info.items():
        rows.append([
            book_info['id'],
            book_code,
            book_info['name_en'],
            book_info['name_ar'],
            book_info['total_hadith'],
            create_slug(book_info['name_en'])
        ])

    write_to_csv('books.csv', headers, rows)
    print(f"[OK] Created books.csv with {len(rows)} books")
    return books_info


def generate_books_localizations_csv(books_info):
    """Generate books_localizations.csv"""
    print("\n=== Generating Books Localizations CSV ===")

    headers = ['id', 'book_id', 'localization_id', 'localization_code', 'name', 'slug']
    rows = []
    row_id = 1

    for book_code, book_info in books_info.items():
        # English localization
        rows.append([
            row_id,
            book_info['id'],
            LOCALIZATION_MAP['en']['id'],
            'en',
            book_info['name_en'],
            create_slug(book_info['name_en'])
        ])
        row_id += 1

        # Arabic localization
        if book_info['name_ar']:
            rows.append([
                row_id,
                book_info['id'],
                LOCALIZATION_MAP['ar']['id'],
                'ar',
                book_info['name_ar'],
                create_slug(book_info['name_ar'])
            ])
            row_id += 1

    write_to_csv('books_localizations.csv', headers, rows)
    print(f"[OK] Created books_localizations.csv with {len(rows)} localizations")
    return len(rows)


def generate_chapters_csv(books_info):
    """Generate chapters.csv using predefined structures"""
    print("\n=== Generating Chapters CSV with Predefined Structures ===")

    headers = ['id', 'book_id', 'chapter_no', 'name_en', 'name_ar', 'total_hadith', 'slug']
    rows = []
    chapter_id = 1

    for book_code, book_info in books_info.items():
        print(f"\n[BOOK] Processing chapters for {book_info['name_en']}...")

        # Use predefined chapter structure
        if book_code in PREDEFINED_CHAPTERS:
            chapter_names = PREDEFINED_CHAPTERS[book_code]
            print(f"  [STRUCT] Using predefined structure with {len(chapter_names)} chapters")

            for chapter_no, chapter_name in enumerate(chapter_names, 1):
                rows.append([
                    chapter_id,
                    book_info['id'],
                    chapter_no,
                    chapter_name,
                    '',  # Arabic name will be in localizations
                    50,  # Estimated hadiths per chapter
                    create_slug(chapter_name)
                ])
                chapter_id += 1

            print(f"  [OK] Added {len(chapter_names)} chapters for {book_info['name_en']}")

        else:
            # Fallback: create generic chapters
            print(f"  [WARN] No predefined structure for {book_info['name_en']}, creating generic chapters")
            num_chapters = book_info.get('chapters', 25)

            for chapter_no in range(1, num_chapters + 1):
                chapter_name = f"The Book of Chapter {chapter_no}"
                rows.append([
                    chapter_id,
                    book_info['id'],
                    chapter_no,
                    chapter_name,
                    '',
                    50,
                    create_slug(chapter_name)
                ])
                chapter_id += 1

            print(f"  [OK] Added {num_chapters} generic chapters for {book_info['name_en']}")

    write_to_csv('chapters.csv', headers, rows)
    print(f"\n[SUCCESS] Created chapters.csv with {len(rows)} TOTAL chapters across all books")

    # Show chapter distribution
    chapter_counts = {}
    for row in rows:
        book_id = row[1]
        chapter_counts[book_id] = chapter_counts.get(book_id, 0) + 1

    print("\n[STATS] Chapter distribution per book:")
    for book_id, count in chapter_counts.items():
        book_name = next((b['name_en'] for b in books_info.values() if b['id'] == book_id), f"Book {book_id}")
        print(f"  {book_name}: {count} chapters")

    return chapter_id - 1


def generate_chapters_localizations_csv(total_chapters, books_info):
    """Generate chapters_localizations.csv"""
    print("\n=== Generating Chapters Localizations CSV ===")

    headers = ['id', 'chapter_id', 'localization_id', 'localization_code', 'name', 'slug']
    rows = []
    row_id = 1
    chapter_id = 1

    for book_code, book_info in books_info.items():
        print(f"🌐 Processing chapter localizations for {book_info['name_en']}...")

        # Use predefined chapter structure for localizations
        if book_code in PREDEFINED_CHAPTERS:
            chapter_names = PREDEFINED_CHAPTERS[book_code]

            for chapter_name in chapter_names:
                rows.append([
                    row_id,
                    chapter_id,
                    LOCALIZATION_MAP['en']['id'],
                    'en',
                    chapter_name,
                    create_slug(chapter_name)
                ])
                row_id += 1
                chapter_id += 1

        else:
            # Generic chapter names
            num_chapters = book_info.get('chapters', 25)
            for i in range(1, num_chapters + 1):
                chapter_name = f"The Book of Chapter {i}"
                rows.append([
                    row_id,
                    chapter_id,
                    LOCALIZATION_MAP['en']['id'],
                    'en',
                    chapter_name,
                    create_slug(chapter_name)
                ])
                row_id += 1
                chapter_id += 1

        print(f"  [OK] Added localizations for {book_info['name_en']}")

    write_to_csv('chapters_localizations.csv', headers, rows)
    print(f"[OK] Created chapters_localizations.csv with {len(rows)} localizations")
    return len(rows)


def generate_categories_csv():
    """Generate categories.csv"""
    print("\n=== Generating Categories CSV ===")

    headers = ['id', 'parent_id', 'name_en', 'name_ar', 'slug']
    rows = []

    # Main categories
    categories = [
        (1, None, 'Faith (Iman)', 'الإيمان', 'faith-iman'),
        (2, None, 'Prayer (Salah)', 'الصلاة', 'prayer-salah'),
        (3, None, 'Purification (Taharah)', 'الطهارة', 'purification-taharah'),
        (4, None, 'Fasting (Sawm)', 'الصوم', 'fasting-sawm'),
        (5, None, 'Charity (Zakat)', 'الزكاة', 'charity-zakat'),
        (6, None, 'Pilgrimage (Hajj)', 'الحج', 'pilgrimage-hajj'),
    ]

    rows.extend(categories)
    write_to_csv('categories.csv', headers, rows)
    print(f"[OK] Created categories.csv with {len(rows)} categories")
    return len(rows)


def generate_category_localizations_csv():
    """Generate category_localizations.csv"""
    print("\n=== Generating Category Localizations CSV ===")

    headers = ['id', 'category_id', 'localization_code', 'name', 'slug']
    rows = []

    # English and Arabic localizations
    localizations = [
        (1, 1, 'en', 'Faith (Iman)', 'faith-iman'),
        (2, 1, 'ar', 'الإيمان', 'faith-iman'),
        (3, 2, 'en', 'Prayer (Salah)', 'prayer-salah'),
        (4, 2, 'ar', 'الصلاة', 'prayer-salah'),
        (5, 3, 'en', 'Purification (Taharah)', 'purification-taharah'),
        (6, 3, 'ar', 'الطهارة', 'purification-taharah'),
        (7, 4, 'en', 'Fasting (Sawm)', 'fasting-sawm'),
        (8, 4, 'ar', 'الصوم', 'fasting-sawm'),
        (9, 5, 'en', 'Charity (Zakat)', 'charity-zakat'),
        (10, 5, 'ar', 'الزكاة', 'charity-zakat'),
        (11, 6, 'en', 'Pilgrimage (Hajj)', 'pilgrimage-hajj'),
        (12, 6, 'ar', 'الحج', 'pilgrimage-hajj'),
    ]

    rows.extend(localizations)
    write_to_csv('category_localizations.csv', headers, rows)
    print(f"[OK] Created category_localizations.csv with {len(rows)} localizations")
    return len(rows)


def main():
    """Main function"""
    print("=" * 60)
    print("STEP 1: GENERATE COMPLETE CHAPTER DATA - FAST VERSION")
    print("=" * 60)
    print("\nThis script will:")
    print("  - Use predefined book and chapter structures")
    print("  - Generate complete CSV files instantly")
    print("  - No API scanning required")
    print("=" * 60)

    # Create CSV output directory
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)

    try:
        # Generate all CSV files
        books_info = generate_books_csv(get_book_info())
        generate_books_localizations_csv(books_info)
        total_chapters = generate_chapters_csv(books_info)
        generate_chapters_localizations_csv(total_chapters, books_info)
        generate_categories_csv()
        generate_category_localizations_csv()

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL CHAPTER DATA GENERATED SUCCESSFULLY!")
        print("=" * 60)

        print(f"\n[DIR] Check the '{CSV_OUTPUT_DIR}' directory")
        print("\nGenerated CSV files contain:")
        print("  - Complete book information")
        print("  - ALL chapters using predefined structures")
        print("  - Comprehensive categories")
        print("  - Multi-language localizations")

        print("\nNext steps:")
        print("1. Run: python step2_import_metadata_from_csv.py")
        print("2. Run: python step4_import_hadiths_fawaz.py")

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()