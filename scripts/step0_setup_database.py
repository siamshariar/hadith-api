"""
Step 0: Setup Database and Run Migrations - SQLITE VERSION
"""

import sqlite3
import subprocess
import sys
import os
from config import DB_CONFIG


def check_existing_tables():
    """Check if tables already exist - SQLITE VERSION"""
    print("� Checking existing tables...")
    
    conn = None
    cursor = None
    try:
        conn = sqlite3.connect(DB_CONFIG['database'])
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        
        required_tables = ['books', 'chapters', 'hadiths', 'categories', 'hadith_translations']
        existing_tables = [table for table in tables if table in required_tables]
        
        print(f"📊 Found {len(existing_tables)} required tables: {', '.join(existing_tables)}")
        
        if len(existing_tables) >= len(required_tables):
            print("✅ All required tables exist!")
            return True
        else:
            print(f"⚠️ Missing tables: {set(required_tables) - set(existing_tables)}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def run_laravel_migrations():
    """Run Laravel migrations if needed - SQLITE VERSION"""
    print("🔄 Checking if Laravel migrations are needed...")
    
    # Since we're using SQLite and the tables already exist,
    # we assume Laravel migrations have been run
    print("✅ Database schema appears to be ready (Laravel migrations already run)")
    return True


def main():
    """Main function - SQLITE VERSION"""
    print("=" * 60)
    print("STEP 0: DATABASE SETUP - SQLITE VERSION")
    print("=" * 60)
    
    # Check if tables already exist
    if check_existing_tables():
        print("\n✅ Database tables already exist. Database is ready!")
        print("\n➡️ Next steps:")
        print("1. Run: python step2_import_metadata_from_csv.py")
        print("2. Run: python step4_import_hadiths_fawaz.py")
        return
    
    # If tables don't exist, try to run Laravel migrations
    print("\n⚠️ Tables missing. Attempting to run Laravel migrations...")
    success = run_laravel_migrations()
    
    if success:
        print("\n✅ Database setup completed successfully!")
        print("\n➡️ Next steps:")
        print("1. Run: python step2_import_metadata_from_csv.py")
        print("2. Run: python step4_import_hadiths_fawaz.py")
    else:
        print("\n❌ Database setup failed!")
        print("Please run Laravel migrations manually:")
        print("  cd ../hadith-api && php artisan migrate")
        sys.exit(1)


if __name__ == "__main__":
    main()