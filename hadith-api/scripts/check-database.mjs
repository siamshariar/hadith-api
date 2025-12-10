// check-database.mjs
import mysql from 'mysql2/promise';

const dbConfig = {
  host: '127.0.0.1',
  port: 3306,
  user: 'root',
  password: '123456',
  database: 'hadith_api_prod'
};

async function checkDatabase() {
  const connection = await mysql.createConnection(dbConfig);
  
  console.log('📊 Database Status Report');
  console.log('='.repeat(50));
  
  // Count records in each table
  const tables = [
    'books', 'chapters', 'categories', 
    'hadiths', 'hadith_translations',
    'books_localizations', 'chapters_localizations',
    'category_localizations', 'hadith_category'
  ];
  
  for (const table of tables) {
    try {
      const [rows] = await connection.execute(`SELECT COUNT(*) as count FROM ${table}`);
      console.log(`📋 ${table}: ${rows[0].count} records`);
    } catch (error) {
      console.log(`❌ ${table}: Table doesn't exist or error: ${error.message}`);
    }
  }
  
  console.log('\n📚 Books Summary:');
  const [books] = await connection.execute('SELECT id, name_en, total_hadith FROM books ORDER BY id');
  for (const book of books) {
    const [hadithCount] = await connection.execute(
      'SELECT COUNT(*) as count FROM hadiths WHERE book_id = ?',
      [book.id]
    );
    console.log(`  Book ${book.id}: ${book.name_en} - ${hadithCount[0].count}/${book.total_hadith} hadiths`);
  }
  
  await connection.end();
}

checkDatabase().catch(console.error);