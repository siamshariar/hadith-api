"""
Utility functions for Hadith API data import - UPDATED WITH PROPER API HANDLING
"""

import mysql.connector
import requests
import time
import csv
import os
from typing import Dict, List, Optional, Any
from config import DB_CONFIG, MAX_RETRIES, RETRY_DELAY, CSV_OUTPUT_DIR, FAWAZ_HADITH_API_EDITIONS


def get_db_connection():
    """Create and return a database connection"""
    return mysql.connector.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database']
    )


def fetch_api_data(url: str, retries: int = MAX_RETRIES, silent: bool = False) -> Optional[Dict]:
    """
    Fetch data from API with retry mechanism - IMPROVED
    """
    for attempt in range(retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=30, headers=headers)
            
            if response.status_code == 404:
                if not silent:
                    print(f"  [404] Not found: {url}")
                return None
                
            response.raise_for_status()
            
            return response.json()
                
        except requests.exceptions.RequestException as e:
            if not silent:
                print(f"  [Attempt {attempt + 1}/{retries}] Error: {e}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                if not silent and "404" not in str(e):
                    print(f"  Failed to fetch after {retries} attempts: {url}")
                return None
        except Exception as e:
            if not silent:
                print(f"  [Attempt {attempt + 1}/{retries}] Unexpected error: {e}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                return None


def fetch_hadith_data(edition_name: str, hadith_number: int, silent: bool = False):
    """
    Fetch hadith data with proper structure handling
    Returns the hadith object or None
    """
    urls = [
        f"{FAWAZ_HADITH_API_EDITIONS}/{edition_name}/{hadith_number}.min.json",
        f"{FAWAZ_HADITH_API_EDITIONS}/{edition_name}/{hadith_number}.json"
    ]
    
    for url in urls:
        data = fetch_api_data(url, silent=silent)
        if data:
            # Handle the hadiths array structure
            if 'hadiths' in data and data['hadiths']:
                return data['hadiths'][0]  # Return first hadith in array
            elif 'hadith' in data:
                return data['hadith']  # Return single hadith object
    return None


def create_slug(text: str) -> str:
    """
    Create URL-friendly slug from text
    """
    import re
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def ensure_csv_directory():
    """Create CSV output directory if it doesn't exist"""
    if not os.path.exists(CSV_OUTPUT_DIR):
        os.makedirs(CSV_OUTPUT_DIR)
        print(f"Created directory: {CSV_OUTPUT_DIR}")


def write_to_csv(filename: str, headers: List[str], rows: List[List[Any]]):
    """
    Write data to CSV file
    """
    ensure_csv_directory()
    filepath = os.path.join(CSV_OUTPUT_DIR, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    
    print(f"[OK] Written {len(rows)} rows to {filepath}")


def check_duplicate(cursor, table: str, conditions: Dict[str, Any]) -> bool:
    """
    Check if record already exists in database
    """
    if not conditions:
        return False
        
    where_clause = ' AND '.join([f"{k} = %s" for k in conditions.keys()])
    query = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
    
    try:
        cursor.execute(query, tuple(conditions.values()))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        print(f"[WARN] Duplicate check failed for {table}: {e}")
        return False


def batch_insert(cursor, table: str, columns: List[str], rows: List[tuple], 
                 check_duplicates: bool = True, duplicate_check_cols: List[str] = None):
    """
    Insert multiple rows with duplicate checking
    """
    inserted = 0
    skipped = 0
    
    for row in rows:
        should_insert = True
        
        if check_duplicates and duplicate_check_cols:
            conditions = {}
            for col in duplicate_check_cols:
                if col in columns:
                    col_index = columns.index(col)
                    conditions[col] = row[col_index]
            
            if conditions and check_duplicate(cursor, table, conditions):
                skipped += 1
                continue
        
        placeholders = ', '.join(['%s'] * len(columns))
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        try:
            cursor.execute(query, row)
            inserted += 1
        except mysql.connector.IntegrityError as e:
            if "Duplicate entry" in str(e):
                skipped += 1
            else:
                print(f"[ERROR] Error inserting into {table}: {e}")
                skipped += 1
    
    print(f"[OK] Inserted {inserted} rows, skipped {skipped} duplicates in {table}")
    return inserted, skipped


def clean_text(text: str) -> str:
    """
    Clean and normalize text - IMPROVED
    """
    if not text:
        return ''
    
    # Remove extra whitespace but preserve Arabic text structure
    text = ' '.join(text.split())
    
    # Clean common issues but preserve Arabic content
    text = text.replace('\\n', '\n').replace('\\t', '\t')
    text = text.replace('\\"', '"').replace("\\'", "'")
    
    # Remove excessive line breaks but keep paragraph structure
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)
    
    return text.strip()