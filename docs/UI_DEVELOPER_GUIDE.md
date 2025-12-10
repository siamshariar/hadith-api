# Language-Wise References: UI Developer Guide

## For Frontend/UI Developers

This guide shows how to integrate language-wise references into your UI.

---

## Quick Start

### Fetch References
```javascript
// Get hadith with Bengali references
const response = await fetch('http://127.0.0.1:8000/api/hadiths/75455/translations/bn');
const data = await response.json();

// Now you have:
const references = data.data.hadith.references;           // Array of strings
const numberedRefs = data.data.hadith.references_numbered; // Numbered map
```

### Display References
```html
<!-- Option 1: Using array -->
<div class="references">
  <h4>উৎসগুলি (References)</h4>
  <ol>
    <li v-for="ref in hadith.references" :key="ref">
      {{ ref }}
    </li>
  </ol>
</div>

<!-- Option 2: Using numbered mapping -->
<div class="references">
  <h4>উৎসগুলি (References)</h4>
  <ol>
    <li v-for="(ref, num) in hadith.references_numbered" :key="num">
      {{ ref }}
    </li>
  </ol>
</div>
```

---

## API Response Structure

```json
{
  "success": true,
  "data": {
    "hadith": {
      "id": 75455,
      "book_id": 10,
      "chapter_id": 280,
      "hadith_number": "1",
      "arabic_text": "عن أبي موسى...",
      "grade": "صحيح",
      "explanation": "নবী সাল্লাল্লাহু...",
      
      "references": [
        "সহীহ মুসলিম (१/ ५४५) (७९१).",
        "بهجة الناظرين শরহ রিয়াজ... (२/ २३१).",
        "রিয়াজুস সালিহীন من... (पृ.२९९) (१००२).",
        "শরহ রিয়াজ... (४/ ६५७).",
        "কুনুজ রিয়াজ... (१३/ ५)."
      ],
      
      "references_numbered": {
        "1": "সহীহ মুসলিম (१/ ५४५) (७९१).",
        "2": "بهجة الناظرين শরহ রিয়াজ... (२/ २३१).",
        "3": "রিয়াজুস সালিহীন من... (पृ.२९९) (१००२).",
        "4": "শরহ রিয়াজ... (४/ ६५७).",
        "5": "কুনুজ রিয়াজ... (१३/ ५)."
      }
    },
    "translation": {
      "id": 183494,
      "hadith_id": 75455,
      "localization_code": "bn",
      "translation_text": "আবূ মূসা আল-'আশ'আরী..."
    }
  }
}
```

---

## Vue.js Example

### Basic Component
```vue
<template>
  <div class="hadith-view">
    <!-- Main content -->
    <div class="hadith-content">
      <h2>{{ hadith.id }}</h2>
      <p class="arabic">{{ hadith.arabic_text }}</p>
    </div>

    <!-- References Section -->
    <div class="references-section" v-if="hadith.references && hadith.references.length">
      <h3>{{ t('references') }}</h3>
      <ol class="references-list">
        <li v-for="(ref, index) in hadith.references" :key="index" class="reference-item">
          <span class="ref-number">{{ index + 1 }}</span>
          <span class="ref-text">{{ ref }}</span>
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const hadith = ref(null);
const language = ref('bn'); // User's selected language

const fetchHadith = async (hadithId) => {
  const response = await fetch(
    `http://127.0.0.1:8000/api/hadiths/${hadithId}/translations/${language.value}`
  );
  const data = await response.json();
  hadith.value = data.data.hadith;
};

onMounted(() => {
  fetchHadith(75455);
});

const t = (key) => {
  const translations = {
    references: 'উৎসগুলি'
  };
  return translations[key] || key;
};
</script>

<style scoped>
.references-section {
  margin-top: 2rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 4px;
}

.references-list {
  list-style: decimal;
  padding-left: 2rem;
}

.reference-item {
  margin: 0.5rem 0;
  line-height: 1.6;
}

.ref-number {
  font-weight: bold;
  margin-right: 0.5rem;
}
</style>
```

### With Language Selector
```vue
<template>
  <div class="hadith-view">
    <!-- Language Selector -->
    <div class="language-selector">
      <label>Language:</label>
      <select v-model="language" @change="refreshHadith">
        <option value="en">English</option>
        <option value="bn">Bengali (বাংলা)</option>
        <option value="ar">Arabic (العربية)</option>
        <option value="ur">Urdu (اردو)</option>
        <option value="fa">Persian (فارسی)</option>
      </select>
    </div>

    <!-- Hadith Content -->
    <div class="hadith-content">
      <h2>Hadith #{{ hadith?.id }}</h2>
      <p class="arabic">{{ hadith?.arabic_text }}</p>
    </div>

    <!-- References -->
    <div class="references-section" v-if="hadith?.references">
      <h3>References</h3>
      <ol>
        <li v-for="(ref, index) in hadith.references" :key="index">
          {{ ref }}
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';

const hadith = reactive({});
const language = ref('en');

const refreshHadith = async () => {
  const response = await fetch(
    `http://127.0.0.1:8000/api/hadiths/75455/translations/${language.value}`
  );
  const data = await response.json();
  Object.assign(hadith, data.data.hadith);
};

// Load initial data
refreshHadith();
</script>
```

---

## React Example

### Basic Component
```jsx
import React, { useState, useEffect } from 'react';

export function HadithView({ hadithId = 75455 }) {
  const [hadith, setHadith] = useState(null);
  const [language, setLanguage] = useState('bn');

  useEffect(() => {
    const fetchHadith = async () => {
      const response = await fetch(
        `http://127.0.0.1:8000/api/hadiths/${hadithId}/translations/${language}`
      );
      const data = await response.json();
      setHadith(data.data.hadith);
    };

    fetchHadith();
  }, [hadithId, language]);

  if (!hadith) return <div>Loading...</div>;

  return (
    <div className="hadith-view">
      <h2>Hadith #{hadith.id}</h2>
      <p className="arabic">{hadith.arabic_text}</p>

      {hadith.references && hadith.references.length > 0 && (
        <div className="references-section">
          <h3>References</h3>
          <ol>
            {hadith.references.map((ref, index) => (
              <li key={index}>{ref}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
```

### With Error Handling
```jsx
import React, { useState, useEffect } from 'react';

export function HadithViewer() {
  const [hadith, setHadith] = useState(null);
  const [language, setLanguage] = useState('bn');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const languages = [
    { code: 'en', name: 'English' },
    { code: 'bn', name: 'Bengali (বাংলা)' },
    { code: 'ar', name: 'Arabic (العربية)' },
    { code: 'ur', name: 'Urdu (اردو)' },
    { code: 'fa', name: 'Persian (فارسی)' },
  ];

  useEffect(() => {
    const loadHadith = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `http://127.0.0.1:8000/api/hadiths/75455/translations/${language}`
        );
        if (!response.ok) throw new Error('Failed to fetch hadith');
        const data = await response.json();
        setHadith(data.data.hadith);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadHadith();
  }, [language]);

  return (
    <div className="hadith-viewer">
      {/* Language Selector */}
      <div className="controls">
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>

      {/* Loading State */}
      {loading && <div className="loading">Loading...</div>}

      {/* Error State */}
      {error && <div className="error">{error}</div>}

      {/* Content */}
      {hadith && !loading && (
        <>
          <div className="content">
            <h1>Hadith #{hadith.id}</h1>
            <p className="arabic">{hadith.arabic_text}</p>
          </div>

          {/* References */}
          {hadith.references && hadith.references.length > 0 && (
            <div className="references">
              <h2>References</h2>
              <ol>
                {hadith.references.map((ref, idx) => (
                  <li key={idx}>{ref}</li>
                ))}
              </ol>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

---

## Vanilla JavaScript Example

```javascript
// Fetch hadith
async function loadHadith(hadithId, language = 'bn') {
  try {
    const response = await fetch(
      `http://127.0.0.1:8000/api/hadiths/${hadithId}/translations/${language}`
    );
    const data = await response.json();
    return data.data.hadith;
  } catch (error) {
    console.error('Error loading hadith:', error);
    return null;
  }
}

// Display references
function displayReferences(hadith, containerId) {
  const container = document.getElementById(containerId);
  
  if (!hadith.references || hadith.references.length === 0) {
    container.innerHTML = '<p>No references available</p>';
    return;
  }

  const html = `
    <div class="references">
      <h3>References</h3>
      <ol>
        ${hadith.references.map(ref => `<li>${ref}</li>`).join('')}
      </ol>
    </div>
  `;
  
  container.innerHTML = html;
}

// Usage
(async () => {
  const hadith = await loadHadith(75455, 'bn');
  displayReferences(hadith, 'hadith-container');
})();
```

---

## Bootstrap HTML Template

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hadith Viewer</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    .hadith-content {
      padding: 2rem;
      background: #f8f9fa;
      border-radius: 8px;
      margin: 1rem 0;
    }
    
    .arabic {
      font-size: 1.5rem;
      direction: rtl;
      text-align: right;
      font-family: 'Arial', sans-serif;
    }
    
    .references {
      background: #e9ecef;
      padding: 1.5rem;
      border-radius: 8px;
      margin-top: 2rem;
    }
    
    .references ol {
      margin: 1rem 0 0 2rem;
    }
    
    .reference-item {
      margin: 0.5rem 0;
      line-height: 1.8;
    }
  </style>
</head>
<body>
  <div class="container mt-4">
    <h1 class="mb-4">Hadith Reference Viewer</h1>

    <!-- Language Selector -->
    <div class="mb-4">
      <label for="language" class="form-label">Select Language:</label>
      <select id="language" class="form-select" onchange="refreshHadith()">
        <option value="en">English</option>
        <option value="bn" selected>Bengali (বাংলা)</option>
        <option value="ar">Arabic (العربية)</option>
        <option value="ur">Urdu (اردو)</option>
        <option value="fa">Persian (فارسی)</option>
      </select>
    </div>

    <!-- Hadith Content -->
    <div id="hadith-content" class="hadith-content">
      <p>Loading...</p>
    </div>

    <!-- References -->
    <div id="references-container"></div>
  </div>

  <script>
    async function refreshHadith() {
      const language = document.getElementById('language').value;
      const response = await fetch(
        `http://127.0.0.1:8000/api/hadiths/75455/translations/${language}`
      );
      const data = await response.json();
      const hadith = data.data.hadith;

      // Display content
      const contentDiv = document.getElementById('hadith-content');
      contentDiv.innerHTML = `
        <h2>Hadith #${hadith.id}</h2>
        <p class="arabic">${hadith.arabic_text}</p>
        <p><strong>Grade:</strong> ${hadith.grade}</p>
      `;

      // Display references
      const refsDiv = document.getElementById('references-container');
      if (hadith.references && hadith.references.length > 0) {
        const refsList = hadith.references
          .map(ref => `<li class="reference-item">${ref}</li>`)
          .join('');
        refsDiv.innerHTML = `
          <div class="references">
            <h3>References</h3>
            <ol>${refsList}</ol>
          </div>
        `;
      }
    }

    // Load on page load
    refreshHadith();
  </script>
</body>
</html>
```

---

## Data Structure Quick Reference

```javascript
// What you get from the API
{
  hadith: {
    id: 75455,
    references: [           // ← Use this for display
      "Reference 1",
      "Reference 2",
      "Reference 3"
    ],
    references_numbered: {  // ← Or use this for numbered lists
      "1": "Reference 1",
      "2": "Reference 2",
      "3": "Reference 3"
    }
  }
}
```

---

## Best Practices

✅ **Use `references` array** - Direct iteration with `forEach` or `map`  
✅ **Use `references_numbered`** - When you need explicit numbering in UI  
✅ **Add loading states** - API calls can take a moment  
✅ **Handle null/empty** - Not all hadiths have references  
✅ **Cache responses** - To reduce API calls  
✅ **Provide language selector** - Let users choose their language  
✅ **Use native numerals** - They're already localized in the API response  
✅ **CSS for RTL** - Use `direction: rtl` for Arabic/Urdu/Persian text  

---

## Troubleshooting

### References not appearing?
```javascript
// Debug: Check if references exist
console.log(hadith.references);        // Should be array
console.log(hadith.references_numbered); // Should be object
```

### Numbers not localized?
```javascript
// The API already localizes numbers
// So if language is 'bn', you'll get Bengali numerals automatically
// No additional processing needed on frontend!
```

### Encoding issues?
```html
<!-- Ensure UTF-8 encoding -->
<meta charset="UTF-8">
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
```

---

## Summary

1. **Fetch** hadith: `GET /api/hadiths/{id}/translations/{language}`
2. **Get** references: `hadith.references` (array) or `hadith.references_numbered` (object)
3. **Display** as list: Use `<ol>` with `v-for`, `.map()`, or loop
4. **Numbers are already localized** - No additional processing needed!

---

**Happy coding!** 🚀

For more details, see the backend implementation docs.
