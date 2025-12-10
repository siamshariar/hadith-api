"""
Configuration file for Hadith API data import - UPDATED WITH WORKING EDITIONS
"""

# Database Configuration - UPDATED FOR MYSQL
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '123456',
    'database': 'hadith_api_prod'
}

DB_HOST = '127.0.0.1'
DB_USER = 'root'
DB_PASSWORD = '123456'
DB_NAME = 'hadith_api_prod'

# API Endpoints
ALQURAN_BD_API = 'http://alquranbd.com/api'
FAWAZ_HADITH_API_BASE = 'https://raw.githubusercontent.com/fawazahmed0/hadith-api/1'
FAWAZ_HADITH_API_EDITIONS = f'{FAWAZ_HADITH_API_BASE}/editions'
FAWAZ_HADITH_API_INFO = f'{FAWAZ_HADITH_API_BASE}/info.json'

# CSV Output Directory
CSV_OUTPUT_DIR = './csv_exports'

# COMPLETE Language Mapping - All Available Translations from CSV and APIs
LOCALIZATION_MAP = {
    'ar': {'id': 1, 'name': 'Arabic', 'direction': 'rtl'},
    'en': {'id': 2, 'name': 'English', 'direction': 'ltr'},
    'ur': {'id': 3, 'name': 'Urdu', 'direction': 'rtl'},
    'bn': {'id': 4, 'name': 'Bengali', 'direction': 'ltr'},
    'tr': {'id': 5, 'name': 'Turkish', 'direction': 'ltr'},
    'fa': {'id': 6, 'name': 'Persian', 'direction': 'rtl'},
    'fr': {'id': 7, 'name': 'French', 'direction': 'ltr'},
    'de': {'id': 8, 'name': 'German', 'direction': 'ltr'},
    'es': {'id': 9, 'name': 'Spanish', 'direction': 'ltr'},
    'ru': {'id': 10, 'name': 'Russian', 'direction': 'ltr'},
    'id': {'id': 11, 'name': 'Indonesian', 'direction': 'ltr'},
    'ms': {'id': 12, 'name': 'Malay', 'direction': 'ltr'},
    # Additional languages from CSV
    'ml': {'id': 13, 'name': 'Malayalam', 'direction': 'ltr'},
    'pt': {'id': 14, 'name': 'Portuguese', 'direction': 'ltr'},
    'ta': {'id': 15, 'name': 'Tamil', 'direction': 'ltr'},
    'zh': {'id': 16, 'name': 'Chinese', 'direction': 'ltr'},
    'hi': {'id': 17, 'name': 'Hindi', 'direction': 'ltr'},
    'it': {'id': 18, 'name': 'Italian', 'direction': 'ltr'},
    'am': {'id': 19, 'name': 'Amharic', 'direction': 'ltr'},
    'az': {'id': 20, 'name': 'Azerbaijani', 'direction': 'ltr'},
    'bs': {'id': 21, 'name': 'Bosnian', 'direction': 'ltr'},
    'cs': {'id': 22, 'name': 'Czech', 'direction': 'ltr'},
    'ha': {'id': 23, 'name': 'Hausa', 'direction': 'ltr'},
    'ku': {'id': 24, 'name': 'Kurdish', 'direction': 'rtl'},
    'nl': {'id': 25, 'name': 'Dutch', 'direction': 'ltr'},
    'ps': {'id': 26, 'name': 'Pashto', 'direction': 'rtl'},
    'ro': {'id': 27, 'name': 'Romanian', 'direction': 'ltr'},
    'si': {'id': 28, 'name': 'Sinhala', 'direction': 'ltr'},
    'so': {'id': 29, 'name': 'Somali', 'direction': 'ltr'},
    'sq': {'id': 30, 'name': 'Albanian', 'direction': 'ltr'},
    'sv': {'id': 31, 'name': 'Swedish', 'direction': 'ltr'},
    'sw': {'id': 32, 'name': 'Swahili', 'direction': 'ltr'},
    'tg': {'id': 33, 'name': 'Tajik', 'direction': 'ltr'},
    'th': {'id': 34, 'name': 'Thai', 'direction': 'ltr'},
    'ug': {'id': 35, 'name': 'Uyghur', 'direction': 'rtl'},
    'uz': {'id': 36, 'name': 'Uzbek', 'direction': 'ltr'},
    'vi': {'id': 37, 'name': 'Vietnamese', 'direction': 'ltr'},
    'yo': {'id': 38, 'name': 'Yoruba', 'direction': 'ltr'},
    # HadeethEnc additional languages
    'tl': {'id': 39, 'name': 'Tagalog', 'direction': 'ltr'},
}

# Book Code Mapping with WORKING EDITIONS
BOOK_CODE_MAP = {
    'bukhari': {
        'alquran_bd': 'bukhari',
        'fawaz': 'ara-bukhari',
        'name_en': 'Sahih al-Bukhari',
        'name_ar': 'صحيح البخاري',
        'total_hadith': 7563,
        'chapters': 97,
        'available_translations': ['ar', 'en', 'ur', 'bn', 'tr', 'fa', 'fr', 'de', 'es', 'ru', 'id', 'ms']
    },
    'muslim': {
        'alquran_bd': 'muslim',
        'fawaz': 'ara-muslim',
        'name_en': 'Sahih Muslim',
        'name_ar': 'صحيح مسلم',
        'total_hadith': 7563,
        'chapters': 54,
        'available_translations': ['ar', 'en', 'ur', 'bn', 'tr', 'fa']
    },
    'abudawud': {
        'alquran_bd': 'abuDaud',
        'fawaz': 'ara-abudawud',
        'name_en': 'Sunan Abu Dawud',
        'name_ar': 'سنن أبي داود',
        'total_hadith': 5274,
        'chapters': 43,
        'available_translations': ['ar', 'en', 'ur', 'bn', 'tr']
    },
    'tirmidhi': {
        'alquran_bd': 'tirmidi',
        'fawaz': 'ara-tirmizi',
        'name_en': 'Jami al-Tirmidhi',
        'name_ar': 'جامع الترمذي',
        'total_hadith': 3956,
        'chapters': 49,
        'available_translations': ['ar', 'en', 'ur', 'bn', 'tr']
    },
    'ibnmajah': {
        'alquran_bd': 'ibnMajah',
        'fawaz': 'ara-ibnmajah',
        'name_en': "Sunan Ibn Majah",
        'name_ar': 'سنن ابن ماجه',
        'total_hadith': 4341,
        'chapters': 37,
        'available_translations': ['ar', 'en', 'ur', 'bn']
    },
    'nasai': {
        'alquran_bd': '',
        'fawaz': 'ara-nasai',
        'name_en': "Sunan an-Nasa'i",
        'name_ar': 'سنن النسائي',
        'total_hadith': 5762,
        'chapters': 51,
        'available_translations': ['ar', 'en', 'ur']
    },
    'riyadussalihin': {
        'alquran_bd': 'riyadusSalihin',
        'fawaz': 'ara-riyadussalihin',
        'name_en': 'Riyad as-Salihin',
        'name_ar': 'رياض الصالحين',
        'total_hadith': 1896,
        'chapters': 20,
        'available_translations': ['ar', 'en', 'ur', 'fr']
    }
}

# Language to Edition Code Mapping
LANG_TO_EDITION = {
    'ar': 'ara',
    'en': 'eng',
    'ur': 'urd', 
    'bn': 'ben',
    'tr': 'tur',
    'fa': 'per',
    'fr': 'fre',
    'de': 'ger',
    'es': 'spa',
    'ru': 'rus',
    'id': 'ind',
    'ms': 'mal'
}

# PREDEFINED CHAPTER STRUCTURES FOR EACH BOOK
PREDEFINED_CHAPTERS = {
    'bukhari': [
        "Revelation", "Belief", "Knowledge", "Ablution", "Prayer",
        "Funeral Prayer", "Zakat", "Fasting", "Hajj", "Marriage",
        "Divorce", "Business Transactions", "Inheritance", "Gifts",
        "Wills", "Vows", "Oaths", "Food", "Drink", "Clothing",
        "Medicine", "Jihad", "Government", "Judiciary"
    ],
    'muslim': [
        "Faith", "Purification", "Prayer", "Zakat", "Fasting",
        "Hajj", "Marriage", "Divorce", "Business", "Inheritance",
        "Wills", "Vows", "Oaths", "Food", "Clothing", "Good Manners"
    ]
}

# Real categories
REAL_CATEGORIES = {
    'faith': {'en': 'Faith (Iman)', 'ar': 'الإيمان', 'parent': None},
    'prayer': {'en': 'Prayer (Salah)', 'ar': 'الصلاة', 'parent': None},
    'purification': {'en': 'Purification (Taharah)', 'ar': 'الطهارة', 'parent': None},
    'fasting': {'en': 'Fasting (Sawm)', 'ar': 'الصوم', 'parent': None},
    'charity': {'en': 'Charity (Zakat)', 'ar': 'الزكاة', 'parent': None},
    'pilgrimage': {'en': 'Pilgrimage (Hajj)', 'ar': 'الحج', 'parent': None},
}

# OPTIMIZED Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY = 1

# Batch Size for Database Inserts
BATCH_SIZE = 100