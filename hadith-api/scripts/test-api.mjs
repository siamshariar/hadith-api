// F:\backup-hadith-api\hadith-api\hadith-api\scripts\test-api.mjs

import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

async function testAPI() {
  console.log('🌐 Testing API endpoints...');
  console.log('='.repeat(50));
  
  const endpoints = [
    '/',
    '/info',
    '/books',
    '/categories/roots',
    '/random'
  ];
  
  for (const endpoint of endpoints) {
    try {
      console.log(`📡 Testing: ${API_BASE_URL}${endpoint}`);
      const response = await axios.get(`${API_BASE_URL}${endpoint}`);
      console.log(`✅ Status: ${response.status}`);
      
      if (response.data) {
        if (response.data.success !== undefined) {
          console.log(`   Success: ${response.data.success}`);
        }
        if (response.data.data !== undefined) {
          const data = response.data.data;
          if (Array.isArray(data)) {
            console.log(`   Items: ${data.length}`);
            if (data.length > 0) {
              console.log(`   First item: ${JSON.stringify(data[0]).substring(0, 100)}...`);
            }
          } else if (typeof data === 'object') {
            console.log(`   Data keys: ${Object.keys(data).join(', ')}`);
          }
        }
      }
      console.log('─'.repeat(50));
    } catch (error) {
      console.error(`❌ Failed: ${error.message}`);
      console.log('─'.repeat(50));
    }
    
    // Delay between requests
    await new Promise(resolve => setTimeout(resolve, 500));
  }
}

testAPI();