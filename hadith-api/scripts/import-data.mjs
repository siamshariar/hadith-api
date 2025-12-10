// fixed-import.mjs
import fs from 'fs';
import path from 'path';
import mysql from 'mysql2/promise';
import axios from 'axios';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dbConfig = {
  host: '127.0.0.1',
  port: 3306,
  user: 'root',
  password: '123456',
  database: 'hadith_api_prod'
};

const API_BASE_URL = 'http://127.0.0.1:8000/api';
const LANGUAGES = ['en', 'vi', 'ar', 'bn', 'ur', 'tr', 'fr', 'es', 'id', 'ms', 'bs', 'ru', 'fa', 'hi', 'si', 'tl', 'zh'];

// Helper functions
function safeValue(value) {
  return value === undefined || value === null ? null : value;
}

function safeString(value, defaultValue = '') {
  if (value === undefined || value === null) return defaultValue;
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value).substring(0, 5000);
}

// Handle JSON safely
function safeJson(value) {
  if (!value || value === '' || value === 'null' || value === 'undefined') {
    return null;
  }
  
  if (typeof value === 'string') {
    try {
      // Check if it's already valid JSON
      JSON.parse(value);
      return value;
    } catch (e) {
      // If not valid JSON, create a JSON array with the string
      return JSON.stringify([value]);
    }
  }
  
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  
  return JSON.stringify([String(value)]);
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

class FixedDataImporter {
  constructor() {
    this.connection = null;
    this.stats = {
      books: { total: 0, imported: 0, errors: 0 },
      categories: { total: 0, imported: 0, errors: 0 },
      chapters: { total: 0, imported: 0, errors: 0 },
      hadiths: { total: 0, imported: 0, errors: 0 },
      translations: { total: 0, imported: 0, errors: 0 }
    };
    this.importedHadithIds = new Set();
  }

  async connect() {
    try {
      this.connection = await mysql.createConnection(dbConfig);
      console.log('✅ Connected to database');
      return true;
    } catch (error) {
      console.error('❌ Database connection failed:', error.message);
      return false;
    }
  }

  async disconnect() {
    if (this.connection) {
      await this.connection.end();
      console.log('✅ Database connection closed');
    }
  }

  async testAPI() {
    console.log('🔍 Testing API...');
    try {
      const response = await axios.get(`${API_BASE_URL}/info`);
      console.log('✅ API is working');
      return true;
    } catch (error) {
      console.error('❌ API Test Failed:', error.message);
      return false;
    }
  }

  async importBooks() {
    console.log('\n📚 Importing books...');
    try {
      const response = await axios.get(`${API_BASE_URL}/books`);
      const books = response.data.data || response.data;
      this.stats.books.total = books.length;
      
      for (const book of books) {
        try {
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
              safeValue(book.id),
              safeString(book.code || `book_${book.id}`),
              safeString(book.title || book.name_en || book.name || `Book ${book.id}`),
              safeString(book.name_ar || book.arabic_name || ''),
              safeValue(book.hadeeths_count || book.total_hadith || 0),
              safeString(book.slug || `book-${book.id}`)
            ]
          );
          
          this.stats.books.imported++;
          console.log(`✅ Book ${this.stats.books.imported}/${this.stats.books.total}: ${book.title || book.name_en}`);
          
        } catch (error) {
          console.error(`❌ Book ${book.id} failed:`, error.message);
          this.stats.books.errors++;
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to fetch books:', error.message);
    }
  }

  async importCategories() {
    console.log('\n📂 Importing categories...');
    try {
      let allCategories = [];
      let page = 1;
      
      // Fetch all categories
      while (true) {
        try {
          const response = await axios.get(`${API_BASE_URL}/categories?page=${page}`);
          const categories = response.data.data || response.data;
          
          if (!Array.isArray(categories) || categories.length === 0) break;
          
          allCategories = [...allCategories, ...categories];
          console.log(`📄 Page ${page}: ${categories.length} categories`);
          page++;
          await delay(200);
        } catch (error) {
          console.error(`❌ Page ${page} failed:`, error.message);
          break;
        }
      }
      
      this.stats.categories.total = allCategories.length;
      console.log(`📊 Total categories to import: ${this.stats.categories.total}`);
      
      // Import categories
      for (const category of allCategories) {
        try {
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
              safeValue(category.id),
              safeValue(category.parent_id),
              safeString(category.title || category.name_en || category.name || `Category ${category.id}`),
              safeString(category.name_ar || category.arabic_name || ''),
              safeString(category.slug || `category-${category.id}`)
            ]
          );
          
          this.stats.categories.imported++;
          if (this.stats.categories.imported % 100 === 0) {
            console.log(`📊 Progress: ${this.stats.categories.imported}/${this.stats.categories.total} categories`);
          }
          
        } catch (error) {
          console.error(`❌ Category ${category.id} failed:`, error.message);
          this.stats.categories.errors++;
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to import categories:', error.message);
    }
  }

  async importChapters() {
    console.log('\n📄 Importing chapters...');
    try {
      const [books] = await this.connection.execute('SELECT id, name_en FROM books ORDER BY id');
      
      for (const book of books) {
        console.log(`📖 Book: ${book.name_en} (ID: ${book.id})`);
        
        try {
          const response = await axios.get(`${API_BASE_URL}/books/${book.id}/chapters`);
          const chapters = response.data.data || response.data;
          
          for (const chapter of chapters) {
            try {
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
                  safeValue(chapter.id),
                  book.id,
                  safeValue(chapter.chapter_no || chapter.number || chapter.id),
                  safeString(chapter.title || chapter.name_en || chapter.name || `Chapter ${chapter.id}`),
                  safeString(chapter.name_ar || chapter.arabic_name || ''),
                  safeValue(chapter.hadeeths_count || chapter.total_hadith || 0),
                  safeString(chapter.slug || `chapter-${chapter.id}`)
                ]
              );
              
              this.stats.chapters.imported++;
            } catch (error) {
              console.error(`❌ Chapter ${chapter.id} failed:`, error.message);
              this.stats.chapters.errors++;
            }
          }
          
          console.log(`   ✅ Imported ${chapters.length} chapters`);
          
        } catch (error) {
          console.error(`❌ Failed to fetch chapters for book ${book.id}:`, error.message);
        }
        
        await delay(500);
      }
      
    } catch (error) {
      console.error('❌ Failed to import chapters:', error.message);
    }
  }

  async importHadithsFromChapter(bookId, chapterId) {
    try {
      let page = 1;
      let hasMore = true;
      
      while (hasMore && page <= 50) {
        try {
          const response = await axios.get(
            `${API_BASE_URL}/books/${bookId}/chapters/${chapterId}/hadeeths?page=${page}&per_page=20`
          );
          
          const hadiths = response.data.data || response.data;
          
          if (!Array.isArray(hadiths) || hadiths.length === 0) {
            hasMore = false;
            break;
          }
          
          for (const hadith of hadiths) {
            if (this.importedHadithIds.has(hadith.id)) continue;
            
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
                  safeValue(hadith.id),
                  bookId,
                  chapterId,
                  safeString(hadith.hadith_number || hadith.number || hadith.id),
                  safeString(hadith.arabic_text || hadith.text_ar || hadith.hadeeth_ar || hadith.text || ''),
                  safeString(hadith.grade)
                ]
              );
              
              this.importedHadithIds.add(hadith.id);
              this.stats.hadiths.imported++;
              
              // Import translations
              await this.importTranslationsForHadith(hadith.id, bookId);
              
              if (this.stats.hadiths.imported % 100 === 0) {
                console.log(`📊 Total Hadiths: ${this.stats.hadiths.imported}`);
              }
              
            } catch (error) {
              console.error(`❌ Hadith ${hadith.id} failed:`, error.message);
              this.stats.hadiths.errors++;
            }
          }
          
          page++;
          hasMore = hadiths.length === 20;
          await delay(300);
          
        } catch (error) {
          console.error(`❌ Page ${page} failed:`, error.message);
          hasMore = false;
        }
      }
      
    } catch (error) {
      console.error(`❌ Failed to import hadiths for chapter ${chapterId}:`, error.message);
    }
  }

  async importTranslationsForHadith(hadithId, bookId) {
    for (const lang of LANGUAGES) {
      try {
        // Try to get translation
        let translationData = null;
        
        // Try multiple endpoints
        const endpoints = [
          `${API_BASE_URL}/hadiths/${hadithId}/translations/${lang}`,
          `${API_BASE_URL}/books/${bookId}/hadiths/${hadithId}/translations/${lang}`,
          `${API_BASE_URL}/hadeeths/${hadithId}/translations/${lang}`
        ];
        
        for (const endpoint of endpoints) {
          try {
            const response = await axios.get(endpoint);
            translationData = response.data.translation || response.data.data || response.data;
            if (translationData) break;
          } catch (error) {
            continue;
          }
        }
        
        if (!translationData) continue;
        
        // Extract data safely
        const translationText = safeString(
          translationData.translation_text || 
          translationData.text || 
          translationData.hadeeth ||
          translationData.translation ||
          ''
        );
        
        // Handle hints safely - convert to JSON or null
        let hintsValue = null;
        if (translationData.hints) {
          try {
            hintsValue = safeJson(translationData.hints);
          } catch (e) {
            hintsValue = null;
          }
        }
        
        // Handle explanation safely
        const explanation = safeString(translationData.explanation || '');
        
        await this.connection.execute(
          `INSERT INTO hadith_translations (hadith_id, localization_id, localization_code, translation_text, explanation, hints, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, NOW(), NOW())
           ON DUPLICATE KEY UPDATE
           translation_text = VALUES(translation_text),
           explanation = VALUES(explanation),
           hints = VALUES(hints),
           updated_at = NOW()`,
          [
            safeValue(hadithId),
            safeValue(hadithId),
            lang,
            translationText,
            explanation,
            hintsValue
          ]
        );
        
        this.stats.translations.imported++;
        
      } catch (error) {
        // Don't log every failed translation - just count errors
        this.stats.translations.errors++;
      }
      
      await delay(50);
    }
  }

  async importAllHadiths() {
    console.log('\n📜 Importing hadiths from all books...');
    
    try {
      // Get all books
      const [books] = await this.connection.execute(
        'SELECT id, name_en FROM books ORDER BY id'
      );
      
      for (const book of books) {
        console.log(`\n📘 Book: ${book.name_en} (ID: ${book.id})`);
        
        // Get all chapters for this book
        const [chapters] = await this.connection.execute(
          'SELECT id, chapter_no FROM chapters WHERE book_id = ? ORDER BY chapter_no',
          [book.id]
        );
        
        console.log(`   📄 Found ${chapters.length} chapters`);
        
        // Import hadiths from each chapter
        for (const chapter of chapters) {
          console.log(`   📑 Chapter ${chapter.chapter_no} (ID: ${chapter.id})`);
          await this.importHadithsFromChapter(book.id, chapter.id);
          await delay(1000);
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to import hadiths:', error.message);
    }
  }

  async importCategoryHadithRelationships() {
    console.log('\n🔗 Importing category-hadith relationships...');
    
    try {
      // Get all categories
      const [categories] = await this.connection.execute(
        'SELECT id FROM categories ORDER BY id LIMIT 50' // Limit to first 50 for now
      );
      
      console.log(`📋 Processing ${categories.length} categories`);
      
      for (const category of categories) {
        try {
          // Get hadiths for this category
          const response = await axios.get(
            `${API_BASE_URL}/categories/${category.id}?include_hadiths=true&limit=50`
          );
          
          const categoryData = response.data.data || response.data;
          
          if (categoryData && categoryData.hadiths && Array.isArray(categoryData.hadiths)) {
            const hadiths = categoryData.hadiths;
            
            for (const hadith of hadiths) {
              try {
                await this.connection.execute(
                  `INSERT INTO hadith_category (hadith_id, category_id)
                   VALUES (?, ?)
                   ON DUPLICATE KEY UPDATE hadith_id = VALUES(hadith_id)`,
                  [safeValue(hadith.id), safeValue(category.id)]
                );
              } catch (error) {
                // Ignore duplicate errors
              }
            }
            
            if (hadiths.length > 0) {
              console.log(`   🔗 Category ${category.id}: Linked ${hadiths.length} hadiths`);
            }
          }
          
          await delay(500);
          
        } catch (error) {
          console.error(`❌ Category ${category.id} failed:`, error.message);
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to import category relationships:', error.message);
    }
  }

  async updateStatistics() {
    console.log('\n📈 Updating statistics...');
    
    try {
      // Update book hadith counts
      await this.connection.execute(`
        UPDATE books b
        SET total_hadith = (
          SELECT COUNT(*) FROM hadiths h WHERE h.book_id = b.id
        ),
        updated_at = NOW()
      `);
      
      // Update chapter hadith counts
      await this.connection.execute(`
        UPDATE chapters c
        SET total_hadith = (
          SELECT COUNT(*) FROM hadiths h WHERE h.chapter_id = c.id
        ),
        updated_at = NOW()
      `);
      
      console.log('✅ Statistics updated');
      
    } catch (error) {
      console.error('❌ Failed to update statistics:', error.message);
    }
  }

  async runImport() {
    console.log('🚀 Starting Data Import');
    console.log('='.repeat(50));
    console.log(`📡 API Base URL: ${API_BASE_URL}`);
    console.log(`🗄️  Database: ${dbConfig.database}`);
    console.log('='.repeat(50));
    
    const startTime = Date.now();
    
    if (!await this.connect()) return;
    if (!await this.testAPI()) {
      await this.disconnect();
      return;
    }
    
    try {
      // Step 1: Import books
      await this.importBooks();
      
      // Step 2: Import categories
      await this.importCategories();
      
      // Step 3: Import chapters
      await this.importChapters();
      
      // Step 4: Import hadiths
      await this.importAllHadiths();
      
      // Step 5: Import category relationships
      await this.importCategoryHadithRelationships();
      
      // Step 6: Update statistics
      await this.updateStatistics();
      
      // Print final statistics
      const endTime = Date.now();
      const duration = Math.floor((endTime - startTime) / 1000);
      
      console.log('\n' + '='.repeat(50));
      console.log('✅ IMPORT COMPLETE');
      console.log('='.repeat(50));
      console.log(`⏱️  Duration: ${duration} seconds`);
      console.log('\n📊 FINAL STATISTICS:');
      console.log(`   📚 Books: ${this.stats.books.imported} imported (${this.stats.books.errors} errors)`);
      console.log(`   📂 Categories: ${this.stats.categories.imported} imported (${this.stats.categories.errors} errors)`);
      console.log(`   📄 Chapters: ${this.stats.chapters.imported} imported (${this.stats.chapters.errors} errors)`);
      console.log(`   📜 Hadiths: ${this.stats.hadiths.imported} imported (${this.stats.hadiths.errors} errors)`);
      console.log(`   🌍 Translations: ${this.stats.translations.imported} imported (${this.stats.translations.errors} errors)`);
      console.log('='.repeat(50));
      
      // Save statistics
      const statsFile = path.join(__dirname, 'import-stats.json');
      fs.writeFileSync(statsFile, JSON.stringify(this.stats, null, 2));
      console.log(`📝 Statistics saved to: ${statsFile}`);
      
    } catch (error) {
      console.error('❌ Import failed:', error);
    } finally {
      await this.disconnect();
    }
  }
}

// Run the importer
const importer = new FixedDataImporter();
importer.runImport().catch(console.error);