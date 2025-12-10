# reset_database_completely.py
"""
COMPLETE DATABASE RESET - Fixes all database issues
"""

import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def reset_database_completely():
    """Completely reset the database"""
    print("🔄 COMPLETELY RESETTING DATABASE...")
    
    conn = None
    try:
        # Connect to MySQL server
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Drop database if exists
        cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
        print(f"✅ Dropped database: {DB_NAME}")
        
        # Create fresh database
        cursor.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ Created fresh database: {DB_NAME}")
        
        conn.commit()
        print("🎉 Database completely reset!")
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()

def main():
    print("=" * 60)
    print("COMPLETE DATABASE RESET")
    print("=" * 60)
    print("⚠️  This will DELETE ALL DATA and create a fresh database!")
    
    confirm = input("\nAre you sure? This cannot be undone! (yes/no): ")
    if confirm.lower() == 'yes':
        reset_database_completely()
        print("\n✅ Now run: python step0_setup_database.py")
    else:
        print("Reset cancelled.")

if __name__ == "__main__":
    main()