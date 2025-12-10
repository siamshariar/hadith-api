"""
MASTER SCRIPT: Complete Hadith API Data Import - MULTI-LANGUAGE VERSION
Works with all latest fixes and supports all languages
"""

import sys
import subprocess
import time
import os
import shlex
import mysql.connector
from config import CSV_OUTPUT_DIR, DB_CONFIG, LOCALIZATION_MAP


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"🎯 {title}")
    print("=" * 70)


def print_step(step_number, description, status="ℹ️ "):
    """Print step information"""
    print(f"\n{status} STEP {step_number}: {description}")


def check_database_status():
    """Check what steps have already been completed"""
    print_header("🔍 CHECKING CURRENT STATUS")
    
    status = {
        'database_ready': False,
        'migrations_run': False,
        'metadata_imported': False,
        'hadiths_imported': False,
        'hadeethenc_imported': False,
        'csv_files_exist': False,
        'languages_imported': []
    }
    
    # Check if database exists and is accessible
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database']
        )
        cursor = conn.cursor()
        
        # Check if migrations have been run (tables exist) - use MySQL information_schema
        cursor.execute("""
            SELECT TABLE_NAME FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s
        """, (DB_CONFIG['database'],))
        tables = [table[0] for table in cursor.fetchall()]
        
        required_tables = ['books', 'chapters', 'hadiths', 'categories', 'hadith_translations']
        status['migrations_run'] = all(table in tables for table in required_tables)
        status['database_ready'] = True
        
        # Check if metadata is imported
        if status['migrations_run']:
            cursor.execute("SELECT COUNT(*) FROM books")
            books_count = cursor.fetchone()[0]
            status['metadata_imported'] = books_count > 0
            
            cursor.execute("SELECT COUNT(*) FROM hadiths")
            hadiths_count = cursor.fetchone()[0]
            status['hadiths_imported'] = hadiths_count > 0
            
            # Check if HadeethEnc is imported - look for hadiths in hadith_category table
            # (HadeethEnc import links hadiths to categories via hadith_category)
            cursor.execute("SELECT COUNT(DISTINCT hadith_id) FROM hadith_category")
            hadeethenc_check = cursor.fetchone()[0]
            
            # Also check if any translations have explanation (from HadeethEnc)
            cursor.execute("SELECT COUNT(*) FROM hadith_translations WHERE explanation IS NOT NULL")
            has_explanation = cursor.fetchone()[0]
            
            status['hadeethenc_imported'] = hadeethenc_check > 100 or has_explanation > 100
            
            # Check which languages have translations
            cursor.execute("SELECT DISTINCT localization_code FROM hadith_translations")
            status['languages_imported'] = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        status['database_ready'] = False
        status['migrations_run'] = False
        print(f"⚠️ Database connection error: {e}")
    
    # Check if CSV files exist
    required_csv_files = ['books.csv', 'chapters.csv', 'categories.csv']
    csv_dir = CSV_OUTPUT_DIR
    if os.path.exists(csv_dir):
        existing_files = os.listdir(csv_dir)
        status['csv_files_exist'] = all(file in existing_files for file in required_csv_files)
    
    # Print status
    print("📊 CURRENT PROGRESS:")
    print(f"  {'✅' if status['database_ready'] else '❌'} Database: {'Ready' if status['database_ready'] else 'Not ready'}")
    print(f"  {'✅' if status['migrations_run'] else '❌'} Migrations: {'Completed' if status['migrations_run'] else 'Not run'}")
    print(f"  {'✅' if status['metadata_imported'] else '❌'} Metadata: {'Imported' if status['metadata_imported'] else 'Not imported'}")
    print(f"  {'✅' if status['hadiths_imported'] else '❌'} Hadiths (Fawaz): {'Imported' if status['hadiths_imported'] else 'Not imported'}")
    print(f"  {'✅' if status['hadeethenc_imported'] else '❌'} Hadiths (HadeethEnc): {'Imported' if status['hadeethenc_imported'] else 'Not imported'}")
    print(f"  {'✅' if status['csv_files_exist'] else '❌'} CSV Files: {'Available' if status['csv_files_exist'] else 'Not available'}")
    
    if status['languages_imported']:
        print(f"  🌍 Languages: {len(status['languages_imported'])} languages imported")
        for lang_code in status['languages_imported'][:5]:  # Show first 5
            lang_name = LOCALIZATION_MAP.get(lang_code, {}).get('name', lang_code)
            print(f"     • {lang_name}")
        if len(status['languages_imported']) > 5:
            print(f"     • ... and {len(status['languages_imported']) - 5} more")
    
    return status


def determine_next_steps(status):
    """Determine which steps need to be run based on current status"""
    steps_needed = []
    
    if not status['database_ready'] or not status['migrations_run']:
        steps_needed.append('step0_setup_database.py')

    if not status['csv_files_exist']:
        steps_needed.append('step1_generate_complete_chapters.py')

    if not status['metadata_imported'] and status['csv_files_exist']:
        steps_needed.append('step2_import_metadata_from_csv.py')

    # Prefer HadeethEnc first (if missing) before Fawaz bulk import
    if not status['hadeethenc_imported']:
        steps_needed.append('step5_import_hadeethenc_complete.py')

    if not status['hadiths_imported'] or len(status['languages_imported']) <= 1:
        steps_needed.append('step4_import_hadiths_fawaz.py')
    
    return steps_needed


def run_script(script_name, description, expected_time="1-2 min", optional=False):
    """Run a Python script with proper error handling"""
    print_header(f"RUNNING: {description}")
    print(f"📜 Script: {script_name}")
    print(f"⏱️  Expected: {expected_time}")
    print('-' * 70)
    
    start_time = time.time()
    
    try:
        # Allow script_name to include arguments (e.g. 'script.py --test')
        cmd = [sys.executable] + shlex.split(script_name)
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True
        )
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ COMPLETED in {elapsed:.1f}s")
            return True
        else:
            if optional:
                print(f"⚠️  OPTIONAL STEP FAILED (continuing...): {elapsed:.1f}s")
                return True
            else:
                print(f"❌ FAILED after {elapsed:.1f}s")
                return False
                
    except Exception as e:
        elapsed = time.time() - start_time
        if optional:
            print(f"⚠️  OPTIONAL STEP ERROR (continuing...): {e}")
            return True
        else:
            print(f"❌ ERROR: {e}")
            return False


def check_prerequisites():
    """Check if all prerequisites are met"""
    print_header("PREREQUISITES CHECK")
    
    required_files = [
        "config.py",
        "utils.py", 
        "step0_setup_database.py",
        "step1_generate_complete_chapters.py",
        "step2_import_metadata_from_csv.py",
        "step4_import_hadiths_fawaz.py",
        "step5_import_hadeethenc_complete.py"
    ]
    
    optional_files = [
        "check_languages.py",
        "reset_database.py"
    ]
    
    all_ok = True
    print("Required files:")
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            all_ok = False
    
    print("\nOptional files:")
    for file in optional_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"⚠️  {file} (optional)")
    
    if not all_ok:
        print("\n❌ Missing required files. Please check the scripts directory.")
        return False
    
    print("\n✅ All prerequisites met!")
    return True


def install_dependencies():
    """Install required Python dependencies"""
    print_header("DEPENDENCIES CHECK")
    
    try:
        import sqlite3
        import requests
        print("✅ sqlite3: Already installed (built-in)")
        print("✅ requests: Already installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("\nInstalling dependencies...")
        
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "requests"
            ], check=True)
            print("✅ Dependencies installed successfully!")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            print("Please run manually: pip install requests")
            return False


def show_welcome():
    """Show welcome message and options"""
    print_header("HADITH API DATA IMPORT SYSTEM - MULTI-LANGUAGE")
    print("\n📚 This system will import complete hadith data from multiple sources:")
    print("   📖 Fawaz API:")
    print("      • 7 Hadith collections (Bukhari, Muslim, etc.)")
    print("      • 100+ Chapters") 
    print("      • 40,000+ Hadith texts")
    print("      • 🌍 20+ language translations")
    print("   📖 HadeethEnc API:")
    print("      • 3,000+ Hadiths with explanations")
    print("      • Hints, word meanings, and references")
    print("      • 🌍 17 language translations")
    print("      • Arabic, English, Urdu, Bengali, Hindi, Turkish, Persian, French, Spanish, and more!")
    
    # Check current status
    status = check_database_status()
    
    print("\n🎯 OPTIONS:")
    print("1. 🚀 SMART IMPORT (Recommended) - Resumes from current state, all sources")
    print("2. 📊 COMPLETE IMPORT - Runs all steps (fresh start), all sources")
    print("3. 🌍 MULTI-LANGUAGE ONLY - Import only translations (Fawaz)")
    print("4. 📖 HADEETHENC ONLY - Import HadeethEnc with explanations")
    print("5. 🔧 CUSTOM Step-by-Step")
    print("6. 🗑️  Reset Database (if having errors)")
    print("7. 📈 Check Current Status")
    print("8. ❌ Exit")
    
    while True:
        try:
            choice = input("\nSelect option (1-8): ").strip()
            if choice in ['1', '2', '3', '4', '5', '6', '7', '8']:
                return choice, status
            print("❌ Please enter 1, 2, 3, 4, 5, 6, 7, or 8")
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
            sys.exit(0)
        except EOFError:
            print("\n\n👋 Exiting...")
            sys.exit(0)


def run_smart_import(status):
    """Run only the steps that are needed based on current status"""
    print_header("🚀 STARTING SMART IMPORT")
    print("This will resume from where you left off!")
    print("🎯 HadeethEnc translations will be preferred where available")
    
    steps_needed = determine_next_steps(status)
    
    if not steps_needed:
        print("🎉 Nothing to do! All steps are already completed.")
        return True
    
    print("📋 Steps that will be run:")
    for step in steps_needed:
        step_name = step.replace('_', ' ').replace('.py', '').title()
        print(f"  • {step_name}")
    
    script_mapping = {
        'step0_setup_database.py': ('Database setup', '< 1 min', False),
        'step1_generate_complete_chapters.py': ('Generate complete chapter data', '< 1 min', False),
        'step2_import_metadata_from_csv.py': ('Import metadata to database', '< 1 min', False),
        'step4_import_hadiths_fawaz.py': ('Import hadiths in ALL languages (Fawaz)', '30-90 min', False),
        'step5_import_hadeethenc_complete.py': ('Import HadeethEnc with explanations', '120-240 min', False),
    }
    
    for step in steps_needed:
        if step in script_mapping:
            description, expected_time, optional = script_mapping[step]
            # If Fawaz runs after HadeethEnc, pass --prefer-hadeethenc flag
            if step == 'step4_import_hadiths_fawaz.py' and 'step5_import_hadeethenc_complete.py' in steps_needed:
                step = 'step4_import_hadiths_fawaz.py --prefer-hadeethenc'
            success = run_script(step, description, expected_time, optional)
            if not success and not optional:
                return False
    
    return True


def run_complete_import():
    """Run the complete import process (fresh start)"""
    print_header("📊 STARTING COMPLETE IMPORT")
    print("This will run ALL steps (fresh start)")
    print("🌍 Including ALL available language translations!")
    print("🎯 HadeethEnc translations will be preferred where available")
    
    # Run HadeethEnc import before Fawaz to prefer HadeethEnc data where available
    scripts = [
        ('step0_setup_database.py', 'Database setup', '< 1 min', False),
        ('step1_generate_complete_chapters.py', 'Generate complete chapter data', '< 1 min', False),
        ('step2_import_metadata_from_csv.py', 'Import metadata to database', '< 1 min', False),
        ('step5_import_hadeethenc_complete.py', 'Import HadeethEnc with explanations', '120-240 min', False),
        ('step4_import_hadiths_fawaz.py --prefer-hadeethenc', 'Import hadiths in ALL languages (Fawaz, skip HadeethEnc)', '30-90 min', False),
    ]
    
    for script, description, expected_time, optional in scripts:
        success = run_script(script, description, expected_time, optional)
        if not success and not optional:
            return False
    
    return True


def run_multi_language_only():
    """Run only the multi-language import"""
    print_header("🌍 MULTI-LANGUAGE TRANSLATIONS IMPORT")
    print("This will import ONLY hadith translations in all available languages")
    print("Assumes you already have the database structure and Arabic hadiths")
    
    confirm = input("\nContinue with multi-language import? (y/n): ")
    if confirm.lower() != 'y':
        print("Import cancelled.")
        return True
    
    return run_script('step4_import_hadiths_fawaz.py', 'Import hadiths in ALL languages', '30-90 min', False)


def run_hadeethenc_import():
    """Run only the HadeethEnc import"""
    print_header("📖 HADEETHENC IMPORT WITH EXPLANATIONS")
    print("This will import HadeethEnc hadiths with:")
    print("  • Full explanations")
    print("  • Hints and word meanings")
    print("  • References")
    print("  • 17 language translations")
    print("\n⏱️  This will take approximately 2-4 hours for ~3,000 hadiths")
    
    print("\nImport options:")
    print("1. Full import (~3,000 hadiths, all categories)")
    print("2. Test import (5 hadiths for testing)")
    print("3. Specific category")
    print("4. Cancel")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == '1':
        return run_script('step5_import_hadeethenc_complete.py', 'Import HadeethEnc (Full)', '120-240 min', False)
    elif choice == '2':
        return run_script('step5_import_hadeethenc_complete.py --test', 'Import HadeethEnc (Test)', '< 5 min', False)
    elif choice == '3':
        print("\nAvailable categories:")
        print("  1. Qur'an (59 hadiths)")
        print("  2. Hadith (5 hadiths)")
        print("  3. Creed (441 hadiths)")
        print("  4. Jurisprudence (1347 hadiths)")
        print("  5. Virtues (822 hadiths)")
        print("  6. Da'wah (98 hadiths)")
        print("  7. History (228 hadiths)")
        category_id = input("Enter category ID (1-7): ").strip()
        if category_id in ['1', '2', '3', '4', '5', '6', '7']:
            return run_script(f'step5_import_hadeethenc_complete.py --category {category_id}', 
                            f'Import HadeethEnc Category {category_id}', '10-60 min', False)
        else:
            print("❌ Invalid category ID")
            return False
    else:
        print("Import cancelled.")
        return True


def run_custom_import():
    """Let user select which steps to run"""
    print_header("🔧 CUSTOM STEP-BY-STEP IMPORT")
    
    steps = {
        '1': ('step0_setup_database.py', 'Database setup', '< 1 min'),
        '2': ('step1_generate_complete_chapters.py', 'Generate complete chapter data', '< 1 min'),
        '3': ('step2_import_metadata_from_csv.py', 'Import metadata from CSV', '< 1 min'),
        '4': ('step4_import_hadiths_fawaz.py', 'Import ALL languages (Fawaz)', '30-90 min'),
        '5': ('step5_import_hadeethenc_complete.py', 'Import HadeethEnc with explanations', '120-240 min'),
        '6': ('check_languages.py', 'Check imported languages', '< 1 min'),
        '7': ('reset_database.py', 'Reset database (clear all data)', '< 1 min'),
    }
    
    print("Available steps:")
    for key, (script, desc, time) in steps.items():
        print(f"  {key}. {desc} ({time})")
    
    print("\nEnter step numbers to run (e.g., '1,2,3,4' or 'all'):")
    selection = input("Selection: ").strip()
    
    if selection.lower() == 'all':
        selected_steps = ['1', '2', '3', '4', '5']  # Default complete import
    else:
        selected_steps = [s.strip() for s in selection.split(',')]
    
    for step_key in selected_steps:
        if step_key in steps:
            script, desc, expected_time = steps[step_key]
            success = run_script(script, desc, expected_time)
            if not success and step_key != '7':  # Don't stop for reset failures
                print(f"❌ Stopping due to failure in step {step_key}")
                return False
        else:
            print(f"⚠️  Unknown step: {step_key}")
    
    return True


def reset_database_flow():
    """Handle database reset"""
    print_header("🗑️  DATABASE RESET")
    print("⚠️  This will DELETE ALL DATA from your database!")
    print("Only use this if you're experiencing duplicate errors.")
    
    confirm = input("\nAre you sure you want to reset? (yes/no): ")
    if confirm.lower() == 'yes':
        return run_script('reset_database.py', 'Reset database', '< 1 min')
    else:
        print("Reset cancelled.")
        return True


def show_completion_message(success, total_time, option, status_before):
    """Show completion message with results"""
    print_header("IMPORT COMPLETED")
    
    if success:
        print("🎉 SUCCESS! Your Hadith database is now ready!")
        
        # Show what was accomplished
        status_after = check_database_status()
        
        print("\n📊 ACCOMPLISHED IN THIS SESSION:")
        if not status_before['database_ready'] and status_after['database_ready']:
            print("  ✅ Database created and migrations run")
        if not status_before['csv_files_exist'] and status_after['csv_files_exist']:
            print("  ✅ Chapter extraction completed")
        if not status_before['metadata_imported'] and status_after['metadata_imported']:
            print("  ✅ Metadata imported to database")
        if not status_before['hadiths_imported'] and status_after['hadiths_imported']:
            print("  ✅ Hadith texts imported")
        
        # Show language improvements
        langs_before = len(status_before['languages_imported'])
        langs_after = len(status_after['languages_imported'])
        if langs_after > langs_before:
            print(f"  🌍 Translations in {langs_after} languages imported")
            new_langs = set(status_after['languages_imported']) - set(status_before['languages_imported'])
            if new_langs:
                print(f"     New languages: {', '.join(new_langs)}")
        
        print("\n🚀 NEXT STEPS:")
        print("  1. Build your API endpoints using Laravel")
        print("  2. Test the data with sample queries")
        print("  3. Deploy your Multi-Language Hadith API")
        
        # Show final statistics if available
        try:
            conn = mysql.connector.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database']
            )
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM hadiths")
            total_hadiths = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM hadith_translations")
            total_translations = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT localization_code) FROM hadith_translations")
            total_languages = cursor.fetchone()[0]
            
            print(f"\n📈 FINAL DATABASE STATISTICS:")
            print(f"   📝 Arabic Hadiths: {total_hadiths}")
            print(f"   🌍 Translations: {total_translations}")
            print(f"   🗣️ Languages: {total_languages}")
            print(f"   📚 Total Records: {total_hadiths + total_translations}")
            
            cursor.close()
            conn.close()
        except:
            pass  # Skip if we can't get statistics
        
    else:
        print("❌ IMPORT FAILED")
        print("\nPlease check the errors above and try again.")
        print("You can:")
        print("  - Run individual steps using custom import")
        print("  - Reset the database and try again")
        print("  - Check the troubleshooting guide")
    
    print(f"\n⏱️  Total time: {total_time/60:.1f} minutes")
    print("=" * 70)


def main():
    """Main function - orchestrates the entire import process"""
    try:
        # Start timing
        total_start_time = time.time()
        
        # Welcome and setup
        if not check_prerequisites():
            sys.exit(1)
            
        if not install_dependencies():
            sys.exit(1)
        
        # Show options and get current status
        choice, status_before = show_welcome()
        
        if choice == '8':
            print("\n👋 Exiting. Come back anytime!")
            return
        elif choice == '7':
            check_database_status()
            return
        elif choice == '6':
            success = reset_database_flow()
            total_time = time.time() - total_start_time
            show_completion_message(success, total_time, choice, status_before)
            return
        
        # Run selected import
        success = False
        if choice == '1':
            success = run_smart_import(status_before)
        elif choice == '2':
            success = run_complete_import()
        elif choice == '3':
            success = run_multi_language_only()
        elif choice == '4':
            success = run_hadeethenc_import()
        elif choice == '5':
            success = run_custom_import()
        
        # Show results
        total_time = time.time() - total_start_time
        show_completion_message(success, total_time, choice, status_before)
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Import cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()