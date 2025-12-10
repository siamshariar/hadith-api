// F:\backup-hadith-api\hadith-api\hadith-api\scripts\test-connection.mjs

import mysql from 'mysql2/promise';

const dbConfig = {
  host: '127.0.0.1',
  port: 3306,
  user: 'root',
  password: '123456',
  database: 'hadith_api_prod'
};

async function testConnection() {
  try {
    console.log('🔌 Testing database connection...');
    const connection = await mysql.createConnection(dbConfig);
    console.log('✅ Connected to database successfully!');
    
    // Test query
    const [rows] = await connection.execute('SHOW TABLES');
    console.log('📊 Tables in database:', rows.map(row => Object.values(row)[0]));
    
    await connection.end();
    console.log('✅ Connection closed');
  } catch (error) {
    console.error('❌ Database connection failed:', error.message);
    
    if (error.code === 'ER_BAD_DB_ERROR') {
      console.log('💡 Tip: Create the database first:');
      console.log('   CREATE DATABASE hadith_api_prod;');
    } else if (error.code === 'ER_ACCESS_DENIED_ERROR') {
      console.log('💡 Tip: Check your MySQL username and password');
    }
  }
}

testConnection();