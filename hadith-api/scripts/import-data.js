// F:\hadith-vn-29\hadith-vn\scripts\import-data.js

const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const axios = require('axios');

// Database configuration
const dbConfig = {
  host: '127.0.0.1',
  port: 3306,
  user: 'root',
  password: '123456',
  database: 'hadith_api_prod'
};

// API configuration
const API_BASE_URL = 'http://127.0.0.1:8000/api';
const LANGUAGES = ['en', 'vi', 'ar', 'bn', 'ur', 'tr', 'fr', 'es', 'id', 'ms', 'bs', 'ru', 'fa', 'hi', 'si', 'tl', 'zh'];

class HadithDataImporter {
  constructor() {
    this.connection = null;
    this.stats = {
      books: 0,
      chapters: 0,
      categories: 0,
      hadiths: 0,
      translations: 0,
      errors: 0
    };
  }

  async connectToDatabase() {
    try {
      this.connection = await mysql.createConnection(dbConfig);
      console.log('✅ Connected to database');
    } catch (error) {
      console.error('❌ Database connection failed:', error);
      throw error;
    }
  }

  async disconnect() {
    if (this.connection) {
      await this.connection.end();
      console.log('✅ Database connection closed');
    }
  }

  async importBooks() {
    console.log('📚 Importing books...');
    
    try {
      const response = await axios.get(`${API_BASE_URL}/books`);
      const books = response.data.success ? response.data.data : response.data;
      
      for (const book of books) {
        try {
          // Insert into books table
          await this.connection.execute(
            `INSERT INTO books (id, code, name_en, name_ar, total_hadith, slug, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, NOW(), NOW())
             ON DUPLICATE KEY UPDATE
             name_en = VALUES(name_en),
             name_ar = VALUES(name_ar),
             total_hadith = VALUES(total_hadith),
             slug = VALUES(slug),
             updated_at = NOW()`,
            [
              book.id,
              book.code || `book_${book.id}`,
              book.name_en || book.title || book.name,
              book.name_ar || book.arabic_name,
              book.total_hadith || book.hadiths_count || 0,
              book.slug || `book-${book.id}`
            ]
          );

          // Insert localization records for each language
          for (const lang of LANGUAGES) {
            try {
              const name = book[`name_${lang}`] || book.name_en || book.title || book.name;
              await this.connection.execute(
                `INSERT INTO books_localizations (book_id, localization_id, localization_code, name, slug, created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, NOW(), NOW())
                 ON DUPLICATE KEY UPDATE
                 name = VALUES(name),
                 slug = VALUES(slug),
                 updated_at = NOW()`,
                [
                  book.id,
                  book.id,
                  lang,
                  name,
                  `${book.slug || `book-${book.id}`}-${lang}`
                ]
              );
            } catch (langError) {
              console.warn(`Failed to insert ${lang} localization for book ${book.id}:`, langError.message);
            }
          }

          this.stats.books++;
          console.log(`✅ Imported book: ${book.name_en || book.title}`);
        } catch (bookError) {
          console.error(`❌ Failed to import book ${book.id}:`, bookError.message);
          this.stats.errors++;
        }
      }
    } catch (error) {
      console.error('❌ Failed to fetch books:', error.message);
    }
  }

  async importCategories() {
    console.log('📂 Importing categories...');
    
    try {
      const response = await axios.get(`${API_BASE_URL}/categories?limit=1000`);
      const categories = response.data.success ? response.data.data : response.data;
      
      for (const category of categories) {
        try {
          // Insert into categories table
          await this.connection.execute(
            `INSERT INTO categories (id, parent_id, name_en, name_ar, slug, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, NOW(), NOW())
             ON DUPLICATE KEY UPDATE
             parent_id = VALUES(parent_id),
             name_en = VALUES(name_en),
             name_ar = VALUES(name_ar),
             slug = VALUES(slug),
             updated_at = NOW()`,
            [
              category.id,
              category.parent_id || null,
              category.name_en || category.title || category.name,
              category.name_ar || category.arabic_name,
              category.slug || `category-${category.id}`
            ]
          );

          // Insert localization records
          for (const lang of LANGUAGES) {
            try {
              const name = category[`name_${lang}`] || category.name_en || category.title || category.name;
              await this.connection.execute(
                `INSERT INTO category_localizations (category_id, localization_code, name, slug, created_at, updated_at)
                 VALUES (?, ?, ?, ?, NOW(), NOW())
                 ON DUPLICATE KEY UPDATE
                 name = VALUES(name),
                 slug = VALUES(slug),
                 updated_at = NOW()`,
                [
                  category.id,
                  lang,
                  name,
                  `${category.slug || `category-${category.id}`}-${lang}`
                ]
              );
            } catch (langError) {
              console.warn(`Failed to insert ${lang} localization for category ${category.id}:`, langError.message);
            }
          }

          this.stats.categories++;
        } catch (categoryError) {
          console.error(`❌ Failed to import category ${category.id}:`, categoryError.message);
          this.stats.errors++;
        }
      }
    } catch (error) {
      console.error('❌ Failed to fetch categories:', error.message);
    }
  }

  async importChaptersForBook(bookId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/books/${bookId}/chapters`);
      const chapters = response.data.success ? response.data.data : response.data;
      
      for (const chapter of chapters) {
        try {
          // Insert into chapters table
          await this.connection.execute(
            `INSERT INTO chapters (id, book_id, chapter_no, name_en, name_ar, total_hadith, slug, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), NOW())
             ON DUPLICATE KEY UPDATE
             book_id = VALUES(book_id),
             chapter_no = VALUES(chapter_no),
             name_en = VALUES(name_en),
             name_ar = VALUES(name_ar),
             total_hadith = VALUES(total_hadith),
             slug = VALUES(slug),
             updated_at = NOW()`,
            [
              chapter.id,
              bookId,
              chapter.chapter_no || chapter.number || chapter.id,
              chapter.name_en || chapter.chapter_title || chapter.title || chapter.name,
              chapter.name_ar || chapter.arabic_name,
              chapter.total_hadith || chapter.hadiths_count || 0,
              chapter.slug || `chapter-${chapter.id}`
            ]
          );

          // Insert localization records
          for (const lang of LANGUAGES) {
            try {
              const name = chapter[`name_${lang}`] || chapter.name_en || chapter.chapter_title || chapter.title || chapter.name;
              await this.connection.execute(
                `INSERT INTO chapters_localizations (chapter_id, localization_id, localization_code, name, slug, created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, NOW(), NOW())
                 ON DUPLICATE KEY UPDATE
                 name = VALUES(name),
                 slug = VALUES(slug),
                 updated_at = NOW()`,
                [
                  chapter.id,
                  chapter.id,
                  lang,
                  name,
                  `${chapter.slug || `chapter-${chapter.id}`}-${lang}`
                ]
              );
            } catch (langError) {
              console.warn(`Failed to insert ${lang} localization for chapter ${chapter.id}:`, langError.message);
            }
          }

          this.stats.chapters++;
        } catch (chapterError) {
          console.error(`❌ Failed to import chapter ${chapter.id} for book ${bookId}:`, chapterError.message);
          this.stats.errors++;
        }
      }
    } catch (error) {
      console.error(`❌ Failed to fetch chapters for book ${bookId}:`, error.message);
    }
  }

  async importHadithsForChapter(bookId, chapterId) {
    try {
      let page = 1;
      let hasMore = true;
      
      while (hasMore && page <= 20) {
        try {
          const response = await axios.get(
            `${API_BASE_URL}/books/${bookId}/chapters/${chapterId}/hadeeths?page=${page}&per_page=50`
          );
          
          const hadiths = response.data.success ? response.data.data : response.data;
          
          if (!hadiths || hadiths.length === 0) {
            hasMore = false;
            break;
          }
          
          for (const hadith of hadiths) {
            try {
              // Insert hadith
              await this.connection.execute(
                `INSERT INTO hadiths (id, book_id, chapter_id, hadith_number, arabic_text, grade, created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, NOW(), NOW())
                 ON DUPLICATE KEY UPDATE
                 book_id = VALUES(book_id),
                 chapter_id = VALUES(chapter_id),
                 hadith_number = VALUES(hadith_number),
                 arabic_text = VALUES(arabic_text),
                 grade = VALUES(grade),
                 updated_at = NOW()`,
                [
                  hadith.id,
                  bookId,
                  chapterId,
                  hadith.hadith_number || hadith.number || hadith.id,
                  hadith.arabic_text || hadith.text_ar || hadith.hadeeth_ar || hadith.text || '',
                  hadith.grade ? JSON.stringify(hadith.grade) : null
                ]
              );

              // Import translations
              await this.importTranslationsForHadith(hadith.id, bookId, chapterId);
              
              this.stats.hadiths++;
              
              if (this.stats.hadiths % 100 === 0) {
                console.log(`📊 Progress: ${this.stats.hadiths} hadiths imported`);
              }
            } catch (hadithError) {
              console.error(`❌ Failed to import hadith ${hadith.id}:`, hadithError.message);
              this.stats.errors++;
            }
          }
          
          page++;
          hasMore = hadiths.length === 50;
        } catch (pageError) {
          console.error(`❌ Failed to fetch page ${page}:`, pageError.message);
          hasMore = false;
        }
      }
    } catch (error) {
      console.error(`❌ Failed to fetch hadiths for book ${bookId}, chapter ${chapterId}:`, error.message);
    }
  }

  async importTranslationsForHadith(hadithId, bookId, chapterId) {
    for (const lang of LANGUAGES) {
      try {
        // Try multiple endpoints
        let translation = null;
        
        try {
          const response = await axios.get(
            `${API_BASE_URL}/books/${bookId}/hadiths/${hadithId}/translations/${lang}`
          );
          translation = response.data.success ? response.data.data : response.data;
        } catch (error) {
          // Try alternative endpoint
          try {
            const response = await axios.get(
              `${API_BASE_URL}/hadeeths/${hadithId}/translations/${lang}`
            );
            translation = response.data.success ? response.data.data : response.data;
          } catch (error2) {
            continue; // Skip this language if both endpoints fail
          }
        }
        
        if (translation && (translation.translation_text || translation.translation || translation.text)) {
          await this.connection.execute(
            `INSERT INTO hadith_translations (hadith_id, localization_id, localization_code, translation_text, created_at, updated_at)
             VALUES (?, ?, ?, ?, NOW(), NOW())
             ON DUPLICATE KEY UPDATE
             translation_text = VALUES(translation_text),
             updated_at = NOW()`,
            [
              hadithId,
              hadithId,
              lang,
              translation.translation_text || translation.translation || translation.text
            ]
          );
          
          this.stats.translations++;
        }
      } catch (error) {
        console.warn(`⚠️ Failed to import ${lang} translation for hadith ${hadithId}:`, error.message);
      }
    }
  }

  async importCategoryHadiths(categoryId) {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/categories/${categoryId}?include_hadiths=true&limit=100`
      );
      
      const category = response.data.success ? response.data.data : response.data;
      
      if (category && category.hadiths && Array.isArray(category.hadiths)) {
        for (const hadith of category.hadiths) {
          try {
            // Insert hadith-category relationship
            await this.connection.execute(
              `INSERT INTO hadith_category (hadith_id, category_id)
               VALUES (?, ?)
               ON DUPLICATE KEY UPDATE hadith_id = VALUES(hadith_id)`,
              [hadith.id, categoryId]
            );
          } catch (error) {
            console.warn(`Failed to link hadith ${hadith.id} to category ${categoryId}:`, error.message);
          }
        }
      }
    } catch (error) {
      console.error(`Failed to fetch hadiths for category ${categoryId}:`, error.message);
    }
  }

  async runImport() {
    console.log('🚀 Starting Hadith Data Import');
    console.log('='.repeat(50));
    
    await this.connectToDatabase();
    
    try {
      // Step 1: Import books
      await this.importBooks();
      
      // Step 2: Import categories
      await this.importCategories();
      
      // Step 3: Get list of books to import chapters and hadiths
      const [books] = await this.connection.execute('SELECT id FROM books ORDER BY id LIMIT 10');
      
      for (const book of books) {
        console.log(`\n📖 Processing book ${book.id}...`);
        
        // Step 4: Import chapters for this book
        await this.importChaptersForBook(book.id);
        
        // Step 5: Get chapters for this book
        const [chapters] = await this.connection.execute(
          'SELECT id FROM chapters WHERE book_id = ? ORDER BY id LIMIT 5',
          [book.id]
        );
        
        for (const chapter of chapters) {
          console.log(`   📄 Processing chapter ${chapter.id}...`);
          
          // Step 6: Import hadiths for this chapter
          await this.importHadithsForChapter(book.id, chapter.id);
          
          // Add small delay to avoid rate limiting
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
      
      // Step 7: Import category-hadith relationships
      console.log('\n🔗 Importing category-hadith relationships...');
      const [categories] = await this.connection.execute('SELECT id FROM categories LIMIT 20');
      
      for (const category of categories) {
        await this.importCategoryHadiths(category.id);
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      
      // Print statistics
      console.log('\n' + '='.repeat(50));
      console.log('✅ IMPORT COMPLETE');
      console.log('='.repeat(50));
      console.log('📊 Statistics:');
      console.log(`   Books: ${this.stats.books}`);
      console.log(`   Chapters: ${this.stats.chapters}`);
      console.log(`   Categories: ${this.stats.categories}`);
      console.log(`   Hadiths: ${this.stats.hadiths}`);
      console.log(`   Translations: ${this.stats.translations}`);
      console.log(`   Errors: ${this.stats.errors}`);
      console.log('='.repeat(50));
      
    } catch (error) {
      console.error('❌ Import failed:', error);
    } finally {
      await this.disconnect();
    }
  }
}

// Run the importer
if (require.main === module) {
  const importer = new HadithDataImporter();
  importer.runImport().catch(console.error);
}

module.exports = HadithDataImporter;