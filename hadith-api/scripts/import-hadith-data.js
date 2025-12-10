#!/usr/bin/env node

/**
 * Hadith Data Import Script - Final Working Version
 * Drops and recreates all tables with proper structure
 */

import mysql from 'mysql2/promise';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Database configuration
const dbConfig = {
  host: '127.0.0.1',
  port: 3306,
  user: 'root',
  password: '123456',
  database: 'hadith_api_prod',
  charset: 'utf8mb4',
};

async function disableForeignKeyChecks(connection) {
  await connection.execute('SET FOREIGN_KEY_CHECKS = 0');
  console.log('🔓 Foreign key checks disabled');
}

async function enableForeignKeyChecks(connection) {
  await connection.execute('SET FOREIGN_KEY_CHECKS = 1');
  console.log('🔐 Foreign key checks enabled');
}

async function dropAllTables(connection) {
  console.log('🗑️  Dropping all existing tables...');
  await disableForeignKeyChecks(connection);
  
  const tables = [
    'hadith_categories',
    'hadith_category',
    'hadith_translations',
    'hadiths',
    'categories_localizations',
    'category_localizations',
    'categories',
    'chapter_mappings',
    'chapters_localizations',
    'chapters',
    'books_localizations',
    'books',
  ];
  
  for (const table of tables) {
    try {
      await connection.execute(`DROP TABLE IF EXISTS ${table}`);
      console.log(`  ✅ Dropped: ${table}`);
    } catch (error) {
      console.log(`  ⚠️ Could not drop ${table}: ${error.message}`);
    }
  }
  
  await enableForeignKeyChecks(connection);
  console.log('✅ All tables dropped');
}

async function createTablesWithoutForeignKeys(connection) {
  console.log('\n📊 Creating tables (without foreign keys)...');
  
  // 1. Books table
  await connection.execute(`
    CREATE TABLE books (
      id INT PRIMARY KEY AUTO_INCREMENT,
      code VARCHAR(50) UNIQUE NOT NULL,
      name_en VARCHAR(255) NOT NULL,
      name_ar VARCHAR(255),
      total_hadith INT DEFAULT 0,
      slug VARCHAR(512),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_code (code),
      INDEX idx_slug (slug)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  `);
  console.log('✅ Created table: books');
  
  // 2. Categories table
  await connection.execute(`
    CREATE TABLE categories (
      id INT PRIMARY KEY AUTO_INCREMENT,
      parent_id INT NULL,
      name_en VARCHAR(255) NOT NULL,
      name_ar VARCHAR(255),
      hadiths_count INT DEFAULT 0,
      slug VARCHAR(512),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_parent (parent_id),
      INDEX idx_slug (slug)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  `);
  console.log('✅ Created table: categories');
  
  // 3. Chapters table
  await connection.execute(`
    CREATE TABLE chapters (
      id INT PRIMARY KEY AUTO_INCREMENT,
      book_id INT NOT NULL,
      chapter_no INT NOT NULL,
      name_en VARCHAR(255) NOT NULL,
      name_ar VARCHAR(255),
      total_hadith INT DEFAULT 0,
      slug VARCHAR(512),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_book_chapter (book_id, chapter_no),
      INDEX idx_slug (slug)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  `);
  console.log('✅ Created table: chapters');
  
  // 4. Hadiths table
  await connection.execute(`
    CREATE TABLE hadiths (
      id INT PRIMARY KEY AUTO_INCREMENT,
      book_id INT NOT NULL,
      chapter_id INT NOT NULL,
      hadith_number VARCHAR(50) NOT NULL,
      arabic_text LONGTEXT NOT NULL,
      grade VARCHAR(100),
      narrator TEXT,
      explanation LONGTEXT,
      hints LONGTEXT,
      hadith_references LONGTEXT,
      word_meanings LONGTEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_book_chapter (book_id, chapter_id),
      INDEX idx_hadith_number (hadith_number)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  `);
  console.log('✅ Created table: hadiths');
  
  // 5. Hadith translations table
  await connection.execute(`
    CREATE TABLE hadith_translations (
      id INT PRIMARY KEY AUTO_INCREMENT,
      hadith_id INT NOT NULL,
      language_code VARCHAR(10) NOT NULL,
      translation_text LONGTEXT NOT NULL,
      narrator TEXT,
      explanation LONGTEXT,
      hints LONGTEXT,
      translation_references LONGTEXT,
      word_meanings LONGTEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY idx_hadith_lang (hadith_id, language_code),
      INDEX idx_language (language_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  `);
  console.log('✅ Created table: hadith_translations');
  
  // 6. Hadith categories (many-to-many)
  await connection.execute(`
    CREATE TABLE hadith_categories (
      hadith_id INT NOT NULL,
      category_id INT NOT NULL,
      PRIMARY KEY (hadith_id, category_id),
      INDEX idx_category (category_id),
      INDEX idx_hadith (hadith_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  `);
  console.log('✅ Created table: hadith_categories');
  
  console.log('✅ All tables created without foreign keys');
}

async function addAllForeignKeys(connection) {
  console.log('\n🔗 Adding all foreign keys...');
  await disableForeignKeyChecks(connection);
  
  try {
    // Add self-referencing foreign key to categories
    await connection.execute(`
      ALTER TABLE categories 
      ADD CONSTRAINT fk_categories_parent 
      FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
    `);
    console.log('✅ Added: categories.parent_id → categories.id');
  } catch (error) {
    console.log('⚠️ Could not add categories parent foreign key:', error.message);
  }
  
  try {
    // Add foreign keys for chapters
    await connection.execute(`
      ALTER TABLE chapters 
      ADD CONSTRAINT fk_chapters_book 
      FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
    `);
    console.log('✅ Added: chapters.book_id → books.id');
  } catch (error) {
    console.log('⚠️ Could not add chapters foreign key:', error.message);
  }
  
  try {
    // Add foreign keys for hadiths
    await connection.execute(`
      ALTER TABLE hadiths 
      ADD CONSTRAINT fk_hadiths_book 
      FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
    `);
    console.log('✅ Added: hadiths.book_id → books.id');
  } catch (error) {
    console.log('⚠️ Could not add hadiths book foreign key:', error.message);
  }
  
  try {
    await connection.execute(`
      ALTER TABLE hadiths 
      ADD CONSTRAINT fk_hadiths_chapter 
      FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
    `);
    console.log('✅ Added: hadiths.chapter_id → chapters.id');
  } catch (error) {
    console.log('⚠️ Could not add hadiths chapter foreign key:', error.message);
  }
  
  try {
    // Add foreign key for hadith_translations
    await connection.execute(`
      ALTER TABLE hadith_translations 
      ADD CONSTRAINT fk_hadith_translations_hadith 
      FOREIGN KEY (hadith_id) REFERENCES hadiths(id) ON DELETE CASCADE
    `);
    console.log('✅ Added: hadith_translations.hadith_id → hadiths.id');
  } catch (error) {
    console.log('⚠️ Could not add translations foreign key:', error.message);
  }
  
  try {
    // Add foreign keys for hadith_categories
    await connection.execute(`
      ALTER TABLE hadith_categories 
      ADD CONSTRAINT fk_hadith_categories_hadith 
      FOREIGN KEY (hadith_id) REFERENCES hadiths(id) ON DELETE CASCADE
    `);
    console.log('✅ Added: hadith_categories.hadith_id → hadiths.id');
  } catch (error) {
    console.log('⚠️ Could not add hadith_categories hadith foreign key:', error.message);
  }
  
  try {
    await connection.execute(`
      ALTER TABLE hadith_categories 
      ADD CONSTRAINT fk_hadith_categories_category 
      FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
    `);
    console.log('✅ Added: hadith_categories.category_id → categories.id');
  } catch (error) {
    console.log('⚠️ Could not add hadith_categories category foreign key:', error.message);
  }
  
  await enableForeignKeyChecks(connection);
  console.log('✅ All foreign keys added');
}

async function importSampleData(connection) {
  console.log('\n📦 Importing sample data...');
  
  // 1. Import books
  console.log('📚 Importing books...');
  const books = [
    [1, 'bukhari', 'Sahih Bukhari', 'صحيح البخاري', 7563, 'sahih-bukhari'],
    [2, 'muslim', 'Sahih Muslim', 'صحيح مسلم', 7563, 'sahih-muslim'],
    [3, 'abudawud', 'Sunan Abu Dawud', 'سنن أبي داود', 5274, 'sunan-abu-dawud'],
    [4, 'tirmidhi', 'Jami At-Tirmidhi', 'جامع الترمذي', 3956, 'jami-at-tirmidhi'],
    [5, 'nasai', 'Sunan An-Nasai', 'سنن النسائي', 5762, 'sunan-an-nasai'],
    [6, 'ibnmajah', 'Sunan Ibn Majah', 'سنن ابن ماجه', 4341, 'sunan-ibn-majah'],
    [7, 'malik', 'Muwatta Malik', 'موطأ مالك', 1841, 'muwatta-malik'],
  ];
  
  for (const book of books) {
    await connection.execute(
      `INSERT INTO books (id, code, name_en, name_ar, total_hadith, slug) 
       VALUES (?, ?, ?, ?, ?, ?)`,
      book
    );
  }
  console.log(`✅ Imported ${books.length} books`);
  
  // 2. Import categories
  console.log('📂 Importing categories...');
  const categories = [
    [1, null, 'Faith (Iman)', null, 441, 'faith-iman'],
    [2, null, 'Purification (Taharah)', null, 390, 'purification-taharah'],
    [3, null, 'Prayer (Salah)', null, 1347, 'prayer-salah'],
    [4, 1, 'Belief in Allah', null, 100, 'belief-in-allah'],
    [5, 1, 'Belief in Angels', null, 50, 'belief-in-angels'],
    [6, 3, 'Prayer Times', null, 200, 'prayer-times'],
  ];
  
  for (const category of categories) {
    await connection.execute(
      `INSERT INTO categories (id, parent_id, name_en, name_ar, hadiths_count, slug) 
       VALUES (?, ?, ?, ?, ?, ?)`,
      category
    );
  }
  console.log(`✅ Imported ${categories.length} categories`);
  
  // 3. Import chapters
  console.log('📖 Importing chapters...');
  const chapters = [
    [101, 1, 1, 'Revelation', null, 10, 'revelation'],
    [102, 1, 2, 'Faith', null, 15, 'faith'],
    [103, 1, 3, 'Knowledge', null, 8, 'knowledge'],
    [201, 2, 1, 'Introduction', null, 5, 'introduction'],
    [202, 2, 2, 'Purification', null, 12, 'purification'],
  ];
  
  for (const chapter of chapters) {
    await connection.execute(
      `INSERT INTO chapters (id, book_id, chapter_no, name_en, name_ar, total_hadith, slug) 
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      chapter
    );
  }
  console.log(`✅ Imported ${chapters.length} chapters`);
  
  // 4. Import hadiths
  console.log('📜 Importing hadiths...');
  const hadiths = [
    [1001, 1, 101, 1, 'نص الحديث العربي الأول من صحيح البخاري', 'Sahih', 'Abu Huraira', 
     'Explanation of first hadith', 'Hint 1, Hint 2', 'Sahih Bukhari 1', 'Word meanings for hadith 1'],
    [1002, 1, 101, 2, 'نص الحديث العربي الثاني من صحيح البخاري', 'Sahih', 'Aisha', 
     'Explanation of second hadith', 'Hint A, Hint B', 'Sahih Bukhari 2', 'Word meanings for hadith 2'],
    [2001, 2, 201, 1, 'نص الحديث الأول من صحيح مسلم', 'Sahih', 'Abdullah ibn Masud', 
     'Explanation of the hadith', 'Important hint', 'Sahih Muslim 1', 'Word meanings'],
  ];
  
  for (const hadith of hadiths) {
    await connection.execute(
      `INSERT INTO hadiths (id, book_id, chapter_id, hadith_number, arabic_text, grade, narrator, 
       explanation, hints, hadith_references, word_meanings) 
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      hadith
    );
  }
  console.log(`✅ Imported ${hadiths.length} hadiths`);
  
  // 5. Import translations
  console.log('🌐 Importing translations...');
  const translations = [
    [1001, 'en', 'First hadith text in English from Sahih Bukhari', 'Abu Huraira', 
     'Explanation of first hadith', 'Hint 1, Hint 2', 'Sahih Bukhari 1', 'Word meanings for hadith 1'],
    [1001, 'vi', 'Văn bản hadith đầu tiên bằng tiếng Việt từ Sahih Bukhari', 'Abu Huraira', 
     'Giải thích hadith đầu tiên', 'Gợi ý 1, Gợi ý 2', 'Sahih Bukhari 1', 'Ý nghĩa từ ngữ cho hadith 1'],
    [1001, 'ar', 'النص العربي الأول من صحيح البخاري', 'أبو هريرة', 
     'شرح الحديث الأول', 'تلميح 1، تلميح 2', 'صحيح البخاري 1', 'معاني الكلمات للحديث 1'],
    [1002, 'en', 'Second hadith text in English from Sahih Bukhari', 'Aisha', 
     'Explanation of second hadith', 'Hint A, Hint B', 'Sahih Bukhari 2', 'Word meanings for hadith 2'],
    [2001, 'en', 'First hadith text in English from Sahih Muslim', 'Abdullah ibn Masud', 
     'Explanation of the hadith', 'Important hint', 'Sahih Muslim 1', 'Word meanings'],
  ];
  
  for (const translation of translations) {
    await connection.execute(
      `INSERT INTO hadith_translations (hadith_id, language_code, translation_text, narrator, 
       explanation, hints, translation_references, word_meanings) 
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      translation
    );
  }
  console.log(`✅ Imported ${translations.length} translations`);
  
  // 6. Assign hadiths to categories
  console.log('🏷️  Assigning hadiths to categories...');
  const hadithCategories = [
    [1001, 1], // Hadith 1 to Faith category
    [1001, 4], // Hadith 1 to Belief in Allah subcategory
    [1002, 1], // Hadith 2 to Faith category
    [2001, 3], // Hadith 2001 to Prayer category
  ];
  
  for (const hc of hadithCategories) {
    await connection.execute(
      `INSERT INTO hadith_categories (hadith_id, category_id) VALUES (?, ?)`,
      hc
    );
  }
  console.log(`✅ Assigned ${hadithCategories.length} category relationships`);
}

async function verifyData(connection) {
  console.log('\n🔍 Verifying imported data...');
  
  const queries = [
    ['Books', 'SELECT COUNT(*) as count FROM books'],
    ['Categories', 'SELECT COUNT(*) as count FROM categories'],
    ['Chapters', 'SELECT COUNT(*) as count FROM chapters'],
    ['Hadiths', 'SELECT COUNT(*) as count FROM hadiths'],
    ['Translations', 'SELECT COUNT(*) as count FROM hadith_translations'],
    ['Category assignments', 'SELECT COUNT(*) as count FROM hadith_categories'],
  ];
  
  for (const [name, query] of queries) {
    const [rows] = await connection.execute(query);
    console.log(`  ${name}: ${rows[0].count}`);
  }
  
  console.log('\n📊 Sample data:');
  
  // Show books with hadith counts
  const [booksWithCounts] = await connection.execute(`
    SELECT b.id, b.code, b.name_en, b.total_hadith, 
           COUNT(DISTINCT h.id) as imported_hadiths
    FROM books b
    LEFT JOIN hadiths h ON b.id = h.book_id
    GROUP BY b.id
    ORDER BY b.id
  `);
  console.log('\nBooks with hadith counts:');
  console.table(booksWithCounts);
  
  // Show sample hadith with translations
  const [sampleHadith] = await connection.execute(`
    SELECT 
      h.id,
      h.hadith_number,
      b.name_en as book_name,
      c.name_en as chapter_name,
      h.grade,
      h.narrator,
      GROUP_CONCAT(DISTINCT ht.language_code) as available_languages,
      COUNT(DISTINCT hc.category_id) as category_count
    FROM hadiths h
    JOIN books b ON h.book_id = b.id
    JOIN chapters c ON h.chapter_id = c.id
    LEFT JOIN hadith_translations ht ON h.id = ht.hadith_id
    LEFT JOIN hadith_categories hc ON h.id = hc.hadith_id
    GROUP BY h.id
    ORDER BY h.id
    LIMIT 5
  `);
  console.log('\nSample hadiths:');
  console.table(sampleHadith);
  
  // Show available languages
  const [languages] = await connection.execute(`
    SELECT language_code, COUNT(*) as translation_count
    FROM hadith_translations
    GROUP BY language_code
    ORDER BY translation_count DESC
  `);
  console.log('\nAvailable languages:');
  console.table(languages);
}

async function main() {
  console.log('🚀 Starting Complete Hadith Database Setup\n');
  
  let connection;
  try {
    // Connect to database
    console.log('🔌 Connecting to database...');
    connection = await mysql.createConnection(dbConfig);
    console.log('✅ Connected to MySQL');
    
    // Check MySQL version
    const [version] = await connection.execute('SELECT VERSION() as version');
    console.log(`✅ MySQL Version: ${version[0].version}`);
    
    // Ask for confirmation
    const readline = (await import('readline')).createInterface({
      input: process.stdin,
      output: process.stdout
    });
    
    const question = (query) => new Promise((resolve) => {
      readline.question(query, resolve);
    });
    
    console.log('\n⚠️  WARNING: This will DROP ALL existing tables and create new ones!');
    const confirm = await question('Are you sure you want to continue? (yes/NO): ');
    readline.close();
    
    if (confirm.toLowerCase() !== 'yes') {
      console.log('❌ Operation cancelled by user');
      return;
    }
    
    // Drop all existing tables
    await dropAllTables(connection);
    
    // Create tables without foreign keys first
    await createTablesWithoutForeignKeys(connection);
    
    // Add foreign keys after all tables are created
    await addAllForeignKeys(connection);
    
    // Import sample data
    await importSampleData(connection);
    
    // Verify data
    await verifyData(connection);
    
    console.log('\n🎉 Database setup completed successfully!');
    console.log('\n📚 Next steps:');
    console.log('1. Your API can now use this database structure');
    console.log('2. Update your Laravel models to match the table structure');
    console.log('3. Run your API and test the endpoints');
    console.log('\n📊 Database structure ready for:');
    console.log('   • Books, Chapters, Categories');
    console.log('   • Hadiths with Arabic text');
    console.log('   • Multi-language translations');
    console.log('   • Category assignments');
    
  } catch (error) {
    console.error('\n❌ Fatal error:', error.message);
    console.error(error.stack);
    process.exit(1);
  } finally {
    if (connection) {
      await connection.end();
      console.log('\n✅ Database connection closed');
    }
  }
}

// Run the script
main().catch(console.error);