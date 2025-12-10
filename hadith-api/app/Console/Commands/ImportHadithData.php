<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\Storage;
use Carbon\Carbon;

class ImportHadithData extends Command
{
    protected $signature = 'import:hadith-data 
                            {source? : Data source (hadeethenc, fawazahmed0, both)} 
                            {--all : Import all data including translations}
                            {--books : Import only books}
                            {--categories : Import only categories}
                            {--chapters : Import only chapters}
                            {--hadiths : Import only hadiths}';
    
    protected $description = 'Import hadith data from multiple sources into database';
    
    // Source configurations
    protected $sources = [
        'hadeethenc' => [
            'base_url' => 'https://hadeethenc.com/api/v1',
            'supported_langs' => ['en', 'ar', 'bn', 'bs', 'es', 'fa', 'fr', 'id', 'ru', 'tl', 'tr', 'ur', 'zh', 'hi', 'vi', 'si', 'ug', 'ha', 'ku']
        ],
        'fawazahmed0' => [
            'base_url' => 'https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1',
            'supported_langs' => [
                'ara' => 'Arabic',
                'eng' => 'English',
                'ben' => 'Bengali',
                'urd' => 'Urdu',
                'tur' => 'Turkish',
                'fra' => 'French',
                'ind' => 'Indonesian',
                'rus' => 'Russian',
                'tam' => 'Tamil'
            ]
        ]
    ];
    
    // Book mapping between sources
    protected $bookMapping = [
        'bukhari' => 'Sahih al-Bukhari',
        'muslim' => 'Sahih Muslim',
        'abudawud' => 'Sunan Abu Dawud',
        'tirmidhi' => 'Jami al-Tirmidhi',
        'nasai' => 'Sunan al-Nasa\'i',
        'ibnmajah' => 'Sunan Ibn Majah',
        'malik' => 'Muwatta Malik',
        'nawawi' => 'Riyad as-Salihin',
        'qudsi' => 'Hadith Qudsi',
        'dehlawi' => 'Mishkat al-Masabih'
    ];

    public function handle()
    {
        $source = $this->argument('source') ?? 'both';
        
        $this->info('Starting hadith data import...');
        $this->info('Source: ' . $source);
        
        if ($this->option('all') || !$this->option('books') && !$this->option('categories') && 
            !$this->option('chapters') && !$this->option('hadiths')) {
            
            $this->importAllData($source);
        } else {
            if ($this->option('books')) {
                $this->importBooks($source);
            }
            if ($this->option('categories')) {
                $this->importCategories($source);
            }
            if ($this->option('chapters')) {
                $this->importChapters($source);
            }
            if ($this->option('hadiths')) {
                $this->importHadiths($source);
            }
        }
        
        $this->info('Import completed!');
    }
    
    private function importAllData($source)
    {
        $this->importBooks($source);
        $this->importCategories($source);
        $this->importChapters($source);
        $this->importHadiths($source);
    }
    
    private function importBooks($source)
    {
        $this->info('Importing books...');
        
        if ($source === 'both' || $source === 'hadeethenc') {
            $this->importBooksFromHadeethEnc();
        }
        
        if ($source === 'both' || $source === 'fawazahmed0') {
            $this->importBooksFromFawazAhmed();
        }
    }
    
    private function importBooksFromHadeethEnc()
    {
        try {
            $response = Http::get($this->sources['hadeethenc']['base_url'] . '/categories/roots/?language=en');
            
            if ($response->successful()) {
                $categories = $response->json();
                
                // Create books from categories
                foreach ($categories as $category) {
                    $bookSlug = 'hadeethenc-' . Str::slug($category['title']);
                    
                    // Check if book exists
                    $existingBook = DB::table('books')
                        ->where('code', $bookSlug)
                        ->orWhere('slug', $bookSlug)
                        ->first();
                    
                    if (!$existingBook) {
                        DB::table('books')->insert([
                            'code' => $bookSlug,
                            'name_en' => $category['title'],
                            'name_ar' => $this->translateToArabic($category['title']),
                            'total_hadith' => $category['hadeeths_count'] ?? 0,
                            'slug' => $bookSlug,
                            'created_at' => now(),
                            'updated_at' => now()
                        ]);
                        
                        $this->info("Imported HadeethEnc book: {$category['title']}");
                    }
                }
            }
        } catch (\Exception $e) {
            $this->error("Error importing from HadeethEnc: " . $e->getMessage());
        }
    }
    
    private function importBooksFromFawazAhmed()
    {
        try {
            $response = Http::get($this->sources['fawazahmed0']['base_url'] . '/editions.json');
            
            if ($response->successful()) {
                $editions = $response->json();
                
                foreach ($editions as $editionCode => $editionInfo) {
                    // Parse edition code (e.g., "eng-bukhari")
                    $parts = explode('-', $editionCode);
                    if (count($parts) >= 2) {
                        $langCode = $parts[0];
                        $bookType = $parts[1];
                        
                        if (isset($this->bookMapping[$bookType])) {
                            $bookName = $this->bookMapping[$bookType];
                            $bookSlug = Str::slug($bookName);
                            
                            // Check if book exists
                            $existingBook = DB::table('books')
                                ->where('code', $bookSlug)
                                ->orWhere('slug', $bookSlug)
                                ->first();
                            
                            if (!$existingBook) {
                                $bookId = DB::table('books')->insertGetId([
                                    'code' => $bookSlug,
                                    'name_en' => $bookName,
                                    'name_ar' => $this->translateToArabic($bookName),
                                    'total_hadith' => 0,
                                    'slug' => $bookSlug,
                                    'created_at' => now(),
                                    'updated_at' => now()
                                ]);
                                
                                $this->info("Imported FawazAhmed book: {$bookName}");
                                
                                // Create localization entry
                                DB::table('books_localizations')->insert([
                                    'book_id' => $bookId,
                                    'localization_id' => 1,
                                    'localization_code' => $langCode,
                                    'name' => $editionInfo['name'] ?? $bookName,
                                    'slug' => $editionCode,
                                    'created_at' => now(),
                                    'updated_at' => now()
                                ]);
                            }
                        }
                    }
                }
            }
        } catch (\Exception $e) {
            $this->error("Error importing from FawazAhmed: " . $e->getMessage());
        }
    }
    
    private function importCategories($source)
    {
        $this->info('Importing categories...');
        
        if ($source === 'both' || $source === 'hadeethenc') {
            $this->importCategoriesFromHadeethEnc();
        }
    }
    
    private function importCategoriesFromHadeethEnc()
    {
        try {
            // Import root categories
            $response = Http::get($this->sources['hadeethenc']['base_url'] . '/categories/roots/?language=en');
            
            if ($response->successful()) {
                $categories = $response->json();
                
                foreach ($categories as $category) {
                    $this->importCategory($category, null);
                    
                    // Import subcategories
                    $this->importSubcategories($category['id']);
                }
            }
        } catch (\Exception $e) {
            $this->error("Error importing categories from HadeethEnc: " . $e->getMessage());
        }
    }
    
    private function importCategory($categoryData, $parentId = null)
    {
        $slug = Str::slug($categoryData['title']);
        
        // Check if category exists
        $existingCategory = DB::table('categories')
            ->where('slug', $slug)
            ->first();
        
        if ($existingCategory) {
            // Update existing category
            DB::table('categories')
                ->where('id', $existingCategory->id)
                ->update([
                    'parent_id' => $parentId,
                    'name_en' => $categoryData['title'],
                    'updated_at' => now()
                ]);
            
            $categoryId = $existingCategory->id;
        } else {
            // Create new category
            $categoryId = DB::table('categories')->insertGetId([
                'parent_id' => $parentId,
                'name_en' => $categoryData['title'],
                'name_ar' => $this->translateToArabic($categoryData['title']),
                'slug' => $slug,
                'created_at' => now(),
                'updated_at' => now()
            ]);
            
            $this->info("Imported category: {$categoryData['title']}");
        }
        
        // Create localization entry
        $this->createCategoryLocalization($categoryId, $categoryData);
        
        return $categoryId;
    }
    
    private function importSubcategories($parentId)
    {
        try {
            $response = Http::get($this->sources['hadeethenc']['base_url'] . '/categories/' . $parentId . '/children/?language=en');
            
            if ($response->successful()) {
                $subcategories = $response->json();
                
                foreach ($subcategories as $subcategory) {
                    $subcategoryId = $this->importCategory($subcategory, $parentId);
                    
                    // Recursively import deeper subcategories
                    $this->importSubcategories($subcategory['id']);
                }
            }
        } catch (\Exception $e) {
            // Continue with other subcategories
        }
    }
    
    private function importChapters($source)
    {
        $this->info('Importing chapters...');
        
        // Get all books
        $books = DB::table('books')->get();
        
        foreach ($books as $book) {
            if ($source === 'both' || $source === 'fawazahmed0') {
                $this->importChaptersForBook($book);
            }
        }
    }
    
    private function importChaptersForBook($book)
    {
        try {
            // Try to get chapters from fawazahmed0 API
            $bookCode = str_replace('hadeethenc-', '', $book->code);
            $bookCode = str_replace('-', '', $bookCode);
            
            // Map book name to fawazahmed0 code
            $editionCode = $this->getEditionCode($book->name_en);
            
            if ($editionCode) {
                $response = Http::get($this->sources['fawazahmed0']['base_url'] . '/editions/' . $editionCode . '.json');
                
                if ($response->successful()) {
                    $bookData = $response->json();
                    
                    if (isset($bookData['metadata']['section'])) {
                        $chapterNo = 1;
                        foreach ($bookData['metadata']['section'] as $sectionNumber => $sectionTitle) {
                            $slug = Str::slug($book->slug . '-' . $sectionTitle);
                            
                            // Check if chapter exists
                            $existingChapter = DB::table('chapters')
                                ->where('book_id', $book->id)
                                ->where('slug', $slug)
                                ->first();
                            
                            if (!$existingChapter) {
                                $chapterId = DB::table('chapters')->insertGetId([
                                    'book_id' => $book->id,
                                    'chapter_no' => $chapterNo,
                                    'name_en' => $sectionTitle,
                                    'name_ar' => $this->translateToArabic($sectionTitle),
                                    'total_hadith' => 0,
                                    'slug' => $slug,
                                    'created_at' => now(),
                                    'updated_at' => now()
                                ]);
                                
                                // Create localization entry
                                DB::table('chapters_localizations')->insert([
                                    'chapter_id' => $chapterId,
                                    'localization_id' => 1,
                                    'localization_code' => 'en',
                                    'name' => $sectionTitle,
                                    'slug' => $slug,
                                    'created_at' => now(),
                                    'updated_at' => now()
                                ]);
                                
                                $this->info("Imported chapter: {$sectionTitle} for {$book->name_en}");
                                $chapterNo++;
                            }
                        }
                    }
                }
            }
        } catch (\Exception $e) {
            $this->error("Error importing chapters for {$book->name_en}: " . $e->getMessage());
        }
    }
    
    private function importHadiths($source)
    {
        $this->info('Importing hadiths...');
        
        // Get all books and chapters
        $books = DB::table('books')->get();
        
        foreach ($books as $book) {
            $chapters = DB::table('chapters')->where('book_id', $book->id)->get();
            
            foreach ($chapters as $chapter) {
                if ($source === 'both' || $source === 'fawazahmed0') {
                    $this->importHadithsForChapter($book, $chapter);
                }
                
                if ($source === 'both' || $source === 'hadeethenc') {
                    $this->importHadithsFromCategories($book, $chapter);
                }
            }
        }
    }
    
    private function importHadithsForChapter($book, $chapter)
    {
        try {
            $editionCode = $this->getEditionCode($book->name_en);
            
            if ($editionCode) {
                // Get the specific section data
                $response = Http::get($this->sources['fawazahmed0']['base_url'] . '/editions/' . $editionCode . '/sections/' . $chapter->chapter_no . '.json');
                
                if ($response->successful()) {
                    $sectionData = $response->json();
                    
                    if (isset($sectionData['hadiths'])) {
                        foreach ($sectionData['hadiths'] as $hadithData) {
                            $this->processHadithFromFawazAhmed($hadithData, $book, $chapter);
                        }
                        
                        // Update chapter hadith count
                        DB::table('chapters')
                            ->where('id', $chapter->id)
                            ->update([
                                'total_hadith' => count($sectionData['hadiths']),
                                'updated_at' => now()
                            ]);
                    }
                }
            }
        } catch (\Exception $e) {
            $this->error("Error importing hadiths for chapter {$chapter->name_en}: " . $e->getMessage());
        }
    }
    
    private function processHadithFromFawazAhmed($hadithData, $book, $chapter)
    {
        // Check if hadith already exists
        $existingHadith = DB::table('hadiths')
            ->where('book_id', $book->id)
            ->where('chapter_id', $chapter->id)
            ->where('hadith_number', $hadithData['hadithnumber'])
            ->first();
        
        if (!$existingHadith) {
            $hadithId = DB::table('hadiths')->insertGetId([
                'book_id' => $book->id,
                'chapter_id' => $chapter->id,
                'hadith_number' => $hadithData['hadithnumber'],
                'arabic_text' => $hadithData['text'] ?? '',
                'grade' => $this->extractGrade($hadithData['grades'] ?? []),
                'created_at' => now(),
                'updated_at' => now()
            ]);
            
            $this->info("Imported hadith #{$hadithData['hadithnumber']} for {$book->name_en}");
            
            // Create Arabic translation
            DB::table('hadith_translations')->insert([
                'hadith_id' => $hadithId,
                'localization_id' => 1,
                'localization_code' => 'ar',
                'translation_text' => $hadithData['text'] ?? '',
                'created_at' => now(),
                'updated_at' => now()
            ]);
            
            // Import other language translations
            $this->importTranslationsForHadith($hadithId, $hadithData['hadithnumber'], $book);
        }
    }
    
    private function importTranslationsForHadith($hadithId, $hadithNumber, $book)
    {
        $editionCode = $this->getEditionCode($book->name_en);
        $baseEditionCode = str_replace('ara-', '', $editionCode);
        
        foreach ($this->sources['fawazahmed0']['supported_langs'] as $langCode => $langName) {
            if ($langCode !== 'ara') {
                try {
                    $response = Http::get($this->sources['fawazahmed0']['base_url'] . '/editions/' . $langCode . '-' . $baseEditionCode . '/' . $hadithNumber . '.json');
                    
                    if ($response->successful()) {
                        $translationData = $response->json();
                        
                        if (isset($translationData['text'])) {
                            DB::table('hadith_translations')->insert([
                                'hadith_id' => $hadithId,
                                'localization_id' => 2,
                                'localization_code' => $langCode,
                                'translation_text' => $translationData['text'],
                                'created_at' => now(),
                                'updated_at' => now()
                            ]);
                            
                            $this->info("  -> Imported {$langName} translation for hadith #{$hadithNumber}");
                        }
                    }
                } catch (\Exception $e) {
                    // Skip if translation not available
                }
            }
        }
    }
    
    private function importHadithsFromCategories($book, $chapter)
    {
        try {
            // Get categories for this book
            $categories = DB::table('categories')
                ->where('name_en', 'like', '%' . $book->name_en . '%')
                ->get();
            
            foreach ($categories as $category) {
                $page = 1;
                $hasMore = true;
                
                while ($hasMore && $page < 10) { // Limit to 10 pages
                    $response = Http::get($this->sources['hadeethenc']['base_url'] . '/hadeeths/list/?language=en&category_id=' . $category->id . '&page=' . $page . '&per_page=50');
                    
                    if ($response->successful()) {
                        $data = $response->json();
                        
                        if (isset($data['data']) && count($data['data']) > 0) {
                            foreach ($data['data'] as $hadithInfo) {
                                $this->processHadithFromHadeethEnc($hadithInfo, $book, $chapter, $category);
                            }
                            
                            $hasMore = $page < ($data['meta']['last_page'] ?? 1);
                            $page++;
                        } else {
                            $hasMore = false;
                        }
                    } else {
                        $hasMore = false;
                    }
                }
            }
        } catch (\Exception $e) {
            $this->error("Error importing hadiths from categories: " . $e->getMessage());
        }
    }
    
    private function processHadithFromHadeethEnc($hadithInfo, $book, $chapter, $category)
    {
        try {
            // Get detailed hadith info
            $response = Http::get($this->sources['hadeethenc']['base_url'] . '/hadeeths/one/?language=en&id=' . $hadithInfo['id']);
            
            if ($response->successful()) {
                $hadithData = $response->json();
                
                // Check if hadith exists
                $existingHadith = DB::table('hadiths')
                    ->where('book_id', $book->id)
                    ->where('chapter_id', $chapter->id)
                    ->where('hadith_number', $hadithInfo['id'])
                    ->first();
                
                if (!$existingHadith) {
                    $hadithId = DB::table('hadiths')->insertGetId([
                        'book_id' => $book->id,
                        'chapter_id' => $chapter->id,
                        'hadith_number' => $hadithInfo['id'],
                        'arabic_text' => $hadithData['hadeeth'] ?? '',
                        'grade' => $hadithData['grade'] ?? null,
                        'attribution_ar' => $hadithData['attribution'] ?? null,
                        'created_at' => now(),
                        'updated_at' => now()
                    ]);
                    
                    // Create English translation
                    DB::table('hadith_translations')->insert([
                        'hadith_id' => $hadithId,
                        'localization_id' => 3,
                        'localization_code' => 'en',
                        'translation_text' => $hadithData['title'] ?? '',
                        'hadeeth_intro' => $hadithData['explanation'] ?? null,
                        'attribution' => $hadithData['attribution'] ?? null,
                        'created_at' => now(),
                        'updated_at' => now()
                    ]);
                    
                    // Link hadith to category
                    DB::table('hadith_category')->insert([
                        'hadith_id' => $hadithId,
                        'category_id' => $category->id
                    ]);
                    
                    $this->info("Imported HadeethEnc hadith #{$hadithInfo['id']} for {$book->name_en}");
                    
                    // Import translations in other languages
                    if (isset($hadithInfo['translations'])) {
                        $this->importHadeethEncTranslations($hadithId, $hadithInfo['id'], $hadithInfo['translations']);
                    }
                }
            }
        } catch (\Exception $e) {
            // Continue with next hadith
        }
    }
    
    private function importHadeethEncTranslations($hadithId, $hadithNumber, $availableTranslations)
    {
        foreach ($availableTranslations as $langCode) {
            if ($langCode !== 'en' && $langCode !== 'ar') {
                try {
                    $response = Http::get($this->sources['hadeethenc']['base_url'] . '/hadeeths/one/?language=' . $langCode . '&id=' . $hadithNumber);
                    
                    if ($response->successful()) {
                        $translationData = $response->json();
                        
                        DB::table('hadith_translations')->insert([
                            'hadith_id' => $hadithId,
                            'localization_id' => 4,
                            'localization_code' => $langCode,
                            'translation_text' => $translationData['title'] ?? '',
                            'hadeeth_intro' => $translationData['explanation'] ?? null,
                            'attribution' => $translationData['attribution'] ?? null,
                            'created_at' => now(),
                            'updated_at' => now()
                        ]);
                        
                        $this->info("  -> Imported {$langCode} translation for hadith #{$hadithNumber}");
                    }
                } catch (\Exception $e) {
                    // Skip if translation not available
                }
            }
        }
    }
    
    private function createCategoryLocalization($categoryId, $categoryData)
    {
        // Create English localization
        DB::table('category_localizations')->insert([
            'category_id' => $categoryId,
            'localization_code' => 'en',
            'name' => $categoryData['title'],
            'slug' => Str::slug($categoryData['title']),
            'created_at' => now(),
            'updated_at' => now()
        ]);
        
        // Try to create Arabic localization
        try {
            $arabicName = $this->translateToArabic($categoryData['title']);
            
            DB::table('category_localizations')->insert([
                'category_id' => $categoryId,
                'localization_code' => 'ar',
                'name' => $arabicName,
                'slug' => Str::slug($arabicName),
                'created_at' => now(),
                'updated_at' => now()
            ]);
        } catch (\Exception $e) {
            // Skip Arabic if translation fails
        }
    }
    
    private function extractGrade($grades)
    {
        if (empty($grades)) {
            return null;
        }
        
        // Take the first grade
        $firstGrade = $grades[0];
        return $firstGrade['grade'] ?? null;
    }
    
    private function getEditionCode($bookName)
    {
        $mapping = [
            'Sahih al-Bukhari' => 'ara-bukhari',
            'Sahih Muslim' => 'ara-muslim',
            'Sunan Abu Dawud' => 'ara-abudawud',
            'Jami al-Tirmidhi' => 'ara-tirmidhi',
            'Sunan al-Nasa\'i' => 'ara-nasai',
            'Sunan Ibn Majah' => 'ara-ibnmajah',
            'Muwatta Malik' => 'ara-malik',
            'Riyad as-Salihin' => 'ara-nawawi',
            'Hadith Qudsi' => 'ara-qudsi',
            'Mishkat al-Masabih' => 'ara-dehlawi'
        ];
        
        foreach ($mapping as $name => $code) {
            if (str_contains($bookName, $name) || str_contains($name, $bookName)) {
                return $code;
            }
        }
        
        return null;
    }
    
    private function translateToArabic($text)
    {
        // Simple English to Arabic mapping for common terms
        $translations = [
            'The Noble Qur\'an and Qur\'anic Sciences' => 'القرآن الكريم وعلوم القرآن',
            'The Hadith and Hadith Sciences' => 'الحديث وعلوم الحديث',
            'The Creed' => 'العقيدة',
            'Jurisprudence and Juristic Principles' => 'الفقه وأصول الفقه',
            'Virtues and Manners' => 'الفضائل والآداب',
            'Da\'wah and Hisbah' => 'الدعوة والحسبة',
            'Seerah and History' => 'السيرة والتاريخ',
            'Sahih al-Bukhari' => 'صحيح البخاري',
            'Sahih Muslim' => 'صحيح مسلم',
            'Sunan Abu Dawud' => 'سنن أبي داود',
            'Jami al-Tirmidhi' => 'جامع الترمذي',
            'Sunan al-Nasa\'i' => 'سنن النسائي',
            'Sunan Ibn Majah' => 'سنن ابن ماجه',
            'Muwatta Malik' => 'موطأ مالك',
            'Riyad as-Salihin' => 'رياض الصالحين',
            'Hadith Qudsi' => 'الحديث القدسي',
            'Mishkat al-Masabih' => 'مشكاة المصابيح',
        ];
        
        return $translations[$text] ?? $text;
    }
}