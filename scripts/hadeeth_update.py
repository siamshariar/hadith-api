#!/usr/bin/env python3
"""
HadeethEnc.com Incremental Update Script
Update existing data and fetch new content
"""

import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime, timedelta
from hadeeth_import import HadeethImporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HadeethUpdater(HadeethImporter):
    def __init__(self):
        super().__init__()
    
    def get_last_sync_time(self, sync_type: str) -> datetime:
        """Get last successful sync time for a type"""
        query = """
        SELECT MAX(created_at) as last_sync 
        FROM sync_logs 
        WHERE sync_type = %s AND status = 'success'
        """
        
        try:
            self.cursor.execute(query, (sync_type,))
            result = self.cursor.fetchone()
            if result and result['last_sync']:
                return result['last_sync']
        except Error as e:
            logger.error(f"Error getting last sync time: {e}")
        
        return datetime.now() - timedelta(days=7)  # Default to 7 days ago
    
    def update_categories(self):
        """Update categories"""
        logger.info("Updating categories")
        
        # Get all languages
        self.cursor.execute("SELECT code FROM languages")
        languages = [row['code'] for row in self.cursor.fetchall()]
        
        for language in languages[:3]:  # Limit to first 3 languages
            root_categories = self.get_root_categories(language)
            
            for category in root_categories:
                category_id = int(category.get('id', 0))
                title = category.get('title', '')
                
                # Check if category exists
                self.cursor.execute(
                    "SELECT id FROM categories WHERE id = %s", 
                    (category_id,)
                )
                exists = self.cursor.fetchone()
                
                if not exists:
                    # Insert new category
                    self.insert_category({
                        'id': category_id,
                        'parent_id': category.get('parent_id')
                    })
                    logger.info(f"New category added: {category_id}")
                
                # Update translation
                self.insert_category_translation(category_id, language, title)
    
    def update_hadiths(self):
        """Update hadiths"""
        logger.info("Updating hadiths")
        
        # Get categories with recent updates
        query = """
        SELECT c.id as category_id, l.code as language_code
        FROM categories c
        CROSS JOIN languages l
        WHERE l.code IN ('en', 'ar')
        ORDER BY c.id
        LIMIT 5
        """
        
        try:
            self.cursor.execute(query)
            category_languages = self.cursor.fetchall()
            
            for item in category_languages:
                category_id = item['category_id']
                language = item['language_code']
                
                # Get latest hadiths for this category
                result = self.get_hadiths_by_category(category_id, language, 1, 50)
                
                if not result or 'data' not in result:
                    continue
                
                hadiths = result.get('data', [])
                
                for hadith_summary in hadiths:
                    hadith_id = int(hadith_summary.get('id', 0))
                    
                    # Check if hadith already exists
                    self.cursor.execute(
                        "SELECT id FROM hadiths WHERE id = %s", 
                        (hadith_id,)
                    )
                    exists = self.cursor.fetchone()
                    
                    if not exists:
                        # Fetch and insert new hadith
                        hadith_details = self.get_hadith_details(hadith_id, language)
                        if hadith_details:
                            self.insert_hadith(hadith_details, language)
                            self.insert_hadith_translation(hadith_id, language, hadith_details)
                            self.link_hadith_category(hadith_id, category_id)
                            
                            logger.info(f"New hadith added: {hadith_id}")
                    
                    # Be respectful to the API
                    time.sleep(0.2)
        
        except Error as e:
            logger.error(f"Error updating hadiths: {e}")
    
    def run_update(self):
        """Run incremental update"""
        logger.info("Starting incremental update")
        
        try:
            # Update categories
            self.update_categories()
            
            # Update hadiths
            self.update_hadiths()
            
            logger.info("Update completed successfully")
            
        except Exception as e:
            logger.error(f"Error during update: {e}")
        finally:
            self.close_db()

def main():
    """Main function for update script"""
    print("HadeethEnc.com Incremental Update")
    print("=" * 40)
    
    updater = HadeethUpdater()
    updater.run_update()

if __name__ == "__main__":
    main()