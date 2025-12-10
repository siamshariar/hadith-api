# Hadith API - Complete Setup Guide

This guide will walk you through setting up the Hadith API database from scratch.

## Prerequisites

1. **MySQL Server** (8.0 or higher recommended)
2. **PHP** (8.1 or higher) with Laravel
3. **Python** (3.8 or higher)
4. **Composer** (for Laravel dependencies)

## API Sources Overview

This system can import from two hadith API sources:

### 1. AlQuran BD API
- **URL:** http://alquranbd.com/api/
- **Languages:** English, Bangla, Arabic
- **Status:** May be intermittently unavailable
- **Best for:** Bangla translations

### 2. Fawaz Hadith API (Recommended)
- **URL:** https://raw.githubusercontent.com/fawazahmed0/hadith-api/1
- **Languages:** English, Arabic, Urdu, and more
- **Status:** Stable (GitHub-hosted)
- **Best for:** Multi-language support
- **Structure:** Individual JSON files per hadith

**Note:** The import scripts are configured to use Fawaz API by default since it's more reliable.

## Step-by-Step Setup

### 1. Install Dependencies

#### Python Dependencies
\`\`\`bash
cd scripts
pip install -r requirements.txt
\`\`\`

#### Laravel Dependencies
\`\`\`bash
composer install
\`\`\`

### 2. Configure Environment

#### Database Configuration

Edit `scripts/config.py` with your MySQL credentials:

\`\`\`python
DB_HOST = 'localhost'
DB_USER = 'your_username'
DB_PASSWORD = 'your_password'
DB_NAME = 'hadith_api_prod'
\`\`\`

#### Laravel Environment

Copy `.env.example` to `.env` and configure:

\`\`\`bash
cp .env.example .env
php artisan key:generate
\`\`\`

Update database settings in `.env`:

\`\`\`
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=hadith_api_prod
DB_USERNAME=your_username
DB_PASSWORD=your_password
\`\`\`

### 3. Create Database

Run the database setup script:

\`\`\`bash
cd scripts
python step0_setup_database.py
\`\`\`

This will create the `hadith_api_prod` database if it doesn't exist.

### 4. Run Laravel Migrations

Create all database tables:

\`\`\`bash
php artisan migrate
\`\`\`

This creates:
- `books` - Hadith collections (Bukhari, Muslim, etc.)
- `books_localizations` - Multi-language book names
- `chapters` - Chapters within each book
- `chapters_localizations` - Multi-language chapter names
- `categories` - Hierarchical category tree
- `category_localizations` - Multi-language category names
- `hadiths` - Main hadith texts (Arabic)
- `hadith_translations` - Multi-language translations
- `hadith_category` - Many-to-many relationship
- `chapter_mappings` - Cross-reference between sources

### 5. Import Data

#### Understanding the Import Process

The import happens in stages:

1. **Metadata Generation** - Fetches book and chapter information, creates CSV files
2. **Metadata Import** - Loads CSV data into database tables
3. **Hadith Import** - Fetches individual hadiths with translations

**Important:** The Fawaz API stores each hadith as a separate file (e.g., `ara-bukhari/1.json`, `ara-bukhari/2.json`). The import script will:
- Iterate through hadith numbers (1 to ~10,000)
- Fetch each file individually
- Stop when it encounters 10 consecutive 404 errors
- This process may take 30-60 minutes depending on your connection

#### Option A: Automated Import (Recommended)

Run the master import script:

\`\`\`bash
cd scripts
python import_all.py
\`\`\`

This will:
1. Check database setup
2. Generate metadata CSV files from Fawaz API
3. Import metadata into database
4. Import hadith texts and translations (this step takes the longest)

**Expected Duration:**
- Step 1 (Metadata CSV): 5-10 minutes
- Step 2 (Import CSV): < 1 minute
- Step 3 (Import Hadiths): 30-60 minutes

#### Option B: Manual Step-by-Step Import

If you prefer to run each step manually:

\`\`\`bash
# Step 1: Generate metadata CSV files (5-10 minutes)
python step1_generate_metadata_csv_fawaz.py

# Step 2: Review CSV files (optional)
# Check the csv_exports/ directory

# Step 3: Import metadata from CSV (< 1 minute)
python step2_import_metadata_from_csv.py

# Step 4: Import hadith texts and translations (30-60 minutes)
python step4_import_hadiths_fawaz.py
\`\`\`

**Progress Monitoring:**
- The scripts show progress every 100 hadiths
- You'll see messages like: "Progress: 100 hadiths processed..."
- Don't interrupt the process - it will automatically stop when complete

### 6. Verify Import

Check that data was imported successfully:

\`\`\`sql
-- Check books
SELECT COUNT(*) FROM books;

-- Check hadiths
SELECT COUNT(*) FROM hadiths;

-- Check translations
SELECT COUNT(*) FROM hadith_translations;

-- Sample query
SELECT 
    b.name_en as book,
    h.hadith_number,
    h.text_ar,
    ht.text as translation
FROM hadiths h
JOIN books b ON h.book_id = b.id
LEFT JOIN hadith_translations ht ON h.id = ht.hadith_id
WHERE b.code = 'bukhari'
LIMIT 5;
\`\`\`

## Troubleshooting

### Database Connection Errors

**Error:** `Unknown database 'hadith_api_prod'`

**Solution:** Run `python step0_setup_database.py` first

---

**Error:** `Access denied for user`

**Solution:** Check your MySQL credentials in `config.py` and `.env`

### API Connection Errors

**Error:** `Failed to resolve 'alquranbd.com'`

**Solution:** The AlQuran BD API is currently unreachable. Use the Fawaz API scripts instead:
- Use `step1_generate_metadata_csv_fawaz.py` instead of `step1_generate_metadata_csv.py`
- Skip `step3_import_hadiths_alquranbd.py`
- The `import_all.py` script has been updated to use Fawaz API by default

---

**Error:** `403 Forbidden` from Fawaz API

**Solution:** 
1. The GitHub CDN may be rate-limiting. Wait a few minutes and try again.
2. Check if the repository structure has changed: https://github.com/fawazahmed0/hadith-api
3. The scripts use the raw GitHub URL which is more reliable than CDN

---

**Error:** Import is very slow

**Solution:** This is normal! The Fawaz API requires fetching individual files for each hadith:
- Bukhari has ~7,000 hadiths = 7,000 API calls
- Muslim has ~7,000 hadiths = 7,000 API calls
- Total: ~40,000+ API calls for all books
- Expected time: 30-60 minutes depending on connection speed
- The script shows progress every 100 hadiths

### Character Encoding Issues

**Error:** Arabic text appears as `???` or garbled

**Solution:**
1. Ensure your database uses `utf8mb4` charset
2. Check MySQL configuration:
   \`\`\`sql
   SHOW VARIABLES LIKE 'character_set%';
   \`\`\`
3. All should be `utf8mb4`

## Data Sources

### Fawaz Hadith API (Primary - Recommended)

- **Source:** GitHub repository
- **URL:** `https://raw.githubusercontent.com/fawazahmed0/hadith-api/1/editions/`
- **Structure:** Individual JSON files per hadith
  - Example: `ara-bukhari/1.json`, `ara-bukhari/2.json`, etc.
- **Languages:** Multiple (English, Arabic, Urdu, etc.)
- **Collections:** Bukhari, Muslim, Abu Dawud, Tirmidhi, Ibn Majah, Riyadussalihin
- **Advantages:** 
  - Stable and reliable (GitHub-hosted)
  - Multiple language editions
  - Well-structured data

### AlQuran BD API (Secondary - May be unavailable)

- **Source:** `http://alquranbd.com/api/`
- **Status:** Intermittently unreachable (DNS resolution issues)
- **Languages:** English, Bangla, Arabic
- **Advantages:**
  - Bangla translations
  - Bulk chapter fetching (faster when available)
- **Note:** Scripts have been updated to use Fawaz API as primary source

## Next Steps

After successful import:

1. **Build API Endpoints** - Create Laravel routes and controllers
2. **Add Search Functionality** - Implement full-text search
3. **Create API Documentation** - Document your endpoints
4. **Add Caching** - Implement Redis/Memcached for performance
5. **Set Up Authentication** - If needed for your API
6. **Deploy** - Deploy to production server

## Support

For issues or questions:
1. Check the `TROUBLESHOOTING.md` file
2. Review error logs in the console output
3. Verify all prerequisites are installed correctly

## File Structure

\`\`\`
hadith-api/
├── database/
│   └── migrations/          # Laravel migration files
├── scripts/
│   ├── config.py           # Database and API configuration
│   ├── utils.py            # Helper functions
│   ├── step0_setup_database.py
│   ├── step1_generate_metadata_csv_fawaz.py
│   ├── step2_import_metadata_from_csv.py
│   ├── step4_import_hadiths_fawaz.py
│   ├── import_all.py       # Master import script
│   └── requirements.txt    # Python dependencies
├── csv_exports/            # Generated CSV files (created during import)
├── SETUP_GUIDE.md         # This file
├── TROUBLESHOOTING.md     # Detailed troubleshooting
└── README.md              # Project overview
