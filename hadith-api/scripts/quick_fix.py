#!/usr/bin/env python3
"""
Quick Fix Script for Hadith Database
"""

import json
import mysql.connector
from mysql.connector import Error

# Database Configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'hadith_api_prod',
    'user': 'root',
    'password': '123456'
}

def quick_fix():
    """Fix common issues in the database"""
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    print("🔧 Running quick fixes...")
    
    try:
        # 1. Remove duplicate categories
        print("1. Removing duplicate categories...")
        cursor.execute("""
            DELETE c1 FROM categories c1
            INNER JOIN categories c2 
            WHERE c1.id > c2.id 
            AND c1.name_en = c2.name_en
            AND c1.parent_id <=> c2.parent_id
        """)
        conn.commit()
        print(f"   Removed {cursor.rowcount} duplicate categories")
        
        # 2. Fix subcategory import issue
        print("2. Fixing subcategory structure...")
        cursor.execute("SELECT id, name_en FROM categories WHERE parent_id IS NULL")
        root_categories = cursor.fetchall()
        
        # Create some sample subcategories
        subcategories = [
            "Quranic Sciences",
            "Tafsir",
            "Quran Recitation",
            "Hadith Collection",
            "Hadith Verification",
            "Hadith Terminology",
            "Islamic Beliefs",
            "Monotheism",
            "Prophethood",
            "Prayer",
            "Fasting",
            "Zakat",
            "Hajj",
            "Good Character",
            "Islamic Manners",
            "Purification of Heart",
            "Islamic Propagation",
            "Enjoining Good",
            "Forbidding Evil",
            "Prophet's Biography",
            "Islamic History",
            "Companions' History"
        ]
        
        subcat_count = 0
        for i, root_cat in enumerate(root_categories[:7]):  # First 7 root categories
            for j in range(3):  # Add 3 subcategories per root
                if i*3 + j < len(subcategories):
                    subcat_name = subcategories[i*3 + j]
                    
                    cursor.execute(
                        "SELECT id FROM categories WHERE name_en = %s AND parent_id = %s",
                        (subcat_name, root_cat['id'])
                    )
                    existing = cursor.fetchone()
                    
                    if not existing:
                        cursor.execute("""
                            INSERT INTO categories (name_en, name_ar, slug, parent_id)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            subcat_name,
                            None,
                            f"subcategory-{root_cat['id']}-{j+1}",
                            root_cat['id']
                        ))
                        conn.commit()
                        
                        subcat_id = cursor.lastrowid
                        
                        cursor.execute("""
                            INSERT INTO category_localizations (category_id, localization_code, name, slug)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            subcat_id,
                            'en',
                            subcat_name,
                            f"subcategory-{root_cat['id']}-{j+1}"
                        ))
                        conn.commit()
                        
                        subcat_count += 1
                        print(f"   Added subcategory: {subcat_name} under {root_cat['name_en']}")
        
        print(f"   Added {subcat_count} subcategories")
        
        # 3. Add sample hadiths if none exist
        print("3. Adding sample hadiths...")
        cursor.execute("SELECT COUNT(*) as count FROM hadiths")
        hadith_count = cursor.fetchone()['count']
        
        if hadith_count == 0:
            print("   No hadiths found, adding sample data...")
            
            # Get first book and chapter
            cursor.execute("SELECT id FROM books LIMIT 1")
            book = cursor.fetchone()
            
            cursor.execute("SELECT id FROM chapters WHERE book_id = %s LIMIT 1", (book['id'],))
            chapter = cursor.fetchone()
            
            if book and chapter:
                sample_hadiths = [
                    {
                        'number': 1,
                        'arabic': 'إِنَّمَا الْأَعْمَالُ بِالنِّيَّاتِ، وَإِنَّمَا لِكُلِّ امْرِئٍ مَا نَوَى',
                        'english': 'Actions are according to intentions, and every person will have what they intended.',
                        'grade': 'صحيح'
                    },
                    {
                        'number': 2,
                        'arabic': 'مِنْ حُسْنِ إِسْلَامِ الْمَرْءِ تَرْكُهُ مَا لَا يَعْنِيهِ',
                        'english': 'Part of the perfection of one\'s Islam is leaving that which does not concern him.',
                        'grade': 'حسن'
                    },
                    {
                        'number': 3,
                        'arabic': 'لَا يُؤْمِنُ أَحَدُكُمْ حَتَّى يُحِبَّ لِأَخِيهِ مَا يُحِبُّ لِنَفْسِهِ',
                        'english': 'None of you truly believes until he loves for his brother what he loves for himself.',
                        'grade': 'صحيح'
                    }
                ]
                
                for hadith in sample_hadiths:
                    cursor.execute("""
                        INSERT INTO hadiths (book_id, chapter_id, hadith_number, arabic_text, grade)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        book['id'],
                        chapter['id'],
                        hadith['number'],
                        hadith['arabic'],
                        hadith['grade']
                    ))
                    conn.commit()
                    
                    hadith_id = cursor.lastrowid
                    
                    # Add English translation
                    cursor.execute("""
                        INSERT INTO hadith_translations (hadith_id, localization_id, localization_code, translation_text)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        hadith_id,
                        2,
                        'en',
                        hadith['english']
                    ))
                    conn.commit()
                
                print(f"   Added {len(sample_hadiths)} sample hadiths")
        
        # 4. Update statistics
        print("4. Updating statistics...")
        
        cursor.execute("""
            UPDATE chapters c
            SET total_hadith = (
                SELECT COUNT(*) 
                FROM hadiths h 
                WHERE h.chapter_id = c.id
            )
        """)
        conn.commit()
        
        cursor.execute("""
            UPDATE books b
            SET total_hadith = (
                SELECT COUNT(*) 
                FROM hadiths h 
                WHERE h.book_id = b.id
            )
        """)
        conn.commit()
        
        print("✅ Quick fixes completed!")
        
        # Show final counts
        print("\n📊 Final Statistics:")
        print("=" * 30)
        
        stats = [
            ("Books", "SELECT COUNT(*) as count FROM books"),
            ("Chapters", "SELECT COUNT(*) as count FROM chapters"),
            ("Hadiths", "SELECT COUNT(*) as count FROM hadiths"),
            ("Translations", "SELECT COUNT(*) as count FROM hadith_translations"),
            ("Categories", "SELECT COUNT(*) as count FROM categories"),
            ("Root Categories", "SELECT COUNT(*) as count FROM categories WHERE parent_id IS NULL"),
            ("Subcategories", "SELECT COUNT(*) as count FROM categories WHERE parent_id IS NOT NULL")
        ]
        
        for label, query in stats:
            cursor.execute(query)
            result = cursor.fetchone()
            print(f"{label}: {result['count']}")
        
        print("=" * 30)
        
    except Error as e:
        print(f"❌ Error during quick fix: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    quick_fix()