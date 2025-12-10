<?php
// hadith_import_final.php
// Final improved import script with update capabilities

// Database configuration
$db_host = '127.0.0.1';
$db_port = 3306;
$db_name = 'hadith_api_prod';
$db_user = 'root';
$db_pass = '123456';

// Create database connection
try {
    $pdo = new PDO(
        "mysql:host=$db_host;port=$db_port;dbname=$db_name;charset=utf8mb4",
        $db_user,
        $db_pass,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4"
        ]
    );
    echo "✅ Database connection established.\n";
} catch (PDOException $e) {
    die("❌ Database connection failed: " . $e->getMessage() . "\n");
}

// Configuration
$hadeethenc_base_url = 'https://hadeethenc.com/api/v1';
$fawazahmed_base_url = 'https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1';

// Book mappings - using only major books to start
$book_mappings = [
    'ara-bukhari' => ['code' => 'bukhari', 'name_en' => 'Sahih Bukhari', 'name_ar' => 'صحيح البخاري'],
    'ara-muslim' => ['code' => 'muslim', 'name_en' => 'Sahih Muslim', 'name_ar' => 'صحيح مسلم'],
    'ara-abudawud' => ['code' => 'abudawud', 'name_en' => 'Sunan Abu Dawud', 'name_ar' => 'سنن أبي داود'],
    'ara-tirmidhi' => ['code' => 'tirmidhi', 'name_en' => 'Jami At-Tirmidhi', 'name_ar' => 'جامع الترمذي'],
    'eng-bukhari' => ['code' => 'bukhari', 'name_en' => 'Sahih Bukhari', 'name_ar' => 'صحيح البخاري'],
    'eng-muslim' => ['code' => 'muslim', 'name_en' => 'Sahih Muslim', 'name_ar' => 'صحيح مسلم'],
];

// Language code mappings
$language_codes = [
    'ara' => 'ar', // Arabic
    'eng' => 'en', // English
];

// Helper function to fetch data from URL with retry
function fetchData($url, $retry = 3) {
    for ($i = 0; $i < $retry; $i++) {
        try {
            $context = stream_context_create([
                'http' => [
                    'timeout' => 30,
                    'header' => "User-Agent: HadithImportScript/1.0\r\nAccept: application/json\r\n"
                ],
                'ssl' => [
                    'verify_peer' => false,
                    'verify_peer_name' => false,
                ]
            ]);
            
            $content = @file_get_contents($url, false, $context);
            if ($content !== false) {
                $data = json_decode($content, true);
                if ($data !== null) {
                    return $data;
                }
            }
        } catch (Exception $e) {
            if ($i === $retry - 1) {
                echo "❌ Failed to fetch $url after $retry attempts\n";
            }
            sleep(1);
        }
    }
    return null;
}

// Helper function to generate slug
function generateSlug($text) {
    if (empty($text)) return 'slug';
    
    $text = preg_replace('~[^\pL\d]+~u', '-', $text);
    $text = iconv('utf-8', 'us-ascii//TRANSLIT', $text);
    $text = preg_replace('~[^-\w]+~', '', $text);
    $text = trim($text, '-');
    $text = preg_replace('~-+~', '-', $text);
    $text = strtolower($text);
    return $text ?: 'slug';
}

// 1. Import hadiths from fawazahmed0 API with UPDATE capability
function importFromFawazahmed0($pdo, $update_existing = true) {
    global $fawazahmed_base_url, $book_mappings, $language_codes;
    
    echo "\n📚 Starting fawazahmed0 import...\n";
    if ($update_existing) {
        echo "⚡ Mode: INSERT new hadiths and UPDATE existing ones\n";
    } else {
        echo "⚡ Mode: INSERT new hadiths only (skip existing)\n";
    }
    
    $total_hadiths = 0;
    $total_updated = 0;
    $total_translations = 0;
    $total_skipped = 0;
    
    foreach ($book_mappings as $edition_code => $mapping) {
        echo "\n📖 Processing $edition_code...\n";
        
        // Get book ID or create
        $book_id = getOrCreateBook($pdo, $mapping);
        if (!$book_id) {
            echo "   ❌ Could not get/create book\n";
            continue;
        }
        
        // Extract language
        $parts = explode('-', $edition_code);
        $lang_prefix = $parts[0] ?? 'eng';
        $language_code = isset($language_codes[$lang_prefix]) ? $language_codes[$lang_prefix] : 'en';
        
        // Fetch book data
        $book_url = $fawazahmed_base_url . "/editions/$edition_code.json";
        echo "   🔍 Fetching: $book_url\n";
        
        $book_data = fetchData($book_url);
        if (!$book_data) {
            echo "   ❌ Failed to fetch book data\n";
            continue;
        }
        
        echo "   📊 Book data received:\n";
        echo "     - Hadiths count: " . (isset($book_data['hadiths']) ? count($book_data['hadiths']) : 0) . "\n";
        
        // Process hadiths
        if (isset($book_data['hadiths']) && is_array($book_data['hadiths'])) {
            $result = processHadiths($pdo, $book_id, $book_data['hadiths'], $language_code, $edition_code, $update_existing);
            $total_hadiths += $result['hadiths'];
            $total_updated += $result['updated'];
            $total_translations += $result['translations'];
            $total_skipped += $result['skipped'];
        } else {
            echo "   ⚠️ No hadiths found in book data\n";
        }
        
        echo "   ✅ Completed $edition_code\n";
        sleep(1); // Rate limiting
    }
    
    echo "\n✅ fawazahmed0 import completed:\n";
    echo "   📥 New hadiths: $total_hadiths\n";
    echo "   🔄 Updated hadiths: $total_updated\n";
    echo "   ⏭️  Skipped (already up-to-date): $total_skipped\n";
    echo "   🌐 Translations: $total_translations\n";
    
    return [
        'hadiths' => $total_hadiths, 
        'updated' => $total_updated,
        'skipped' => $total_skipped,
        'translations' => $total_translations
    ];
}

function getOrCreateBook($pdo, $mapping) {
    $book_code = $mapping['code'];
    
    // Check if exists
    $stmt = $pdo->prepare("SELECT id FROM books WHERE code = ?");
    $stmt->execute([$book_code]);
    $existing = $stmt->fetch();
    
    if ($existing) {
        return $existing['id'];
    }
    
    // Create new book
    $slug = generateSlug($mapping['name_en']);
    
    try {
        $stmt = $pdo->prepare("
            INSERT INTO books (code, name_en, name_ar, total_hadith, slug, created_at, updated_at)
            VALUES (?, ?, ?, 0, ?, NOW(), NOW())
        ");
        $stmt->execute([$book_code, $mapping['name_en'], $mapping['name_ar'] ?? null, $slug]);
        
        $book_id = $pdo->lastInsertId();
        
        // Add English localization
        $stmt = $pdo->prepare("
            INSERT INTO books_localizations (book_id, localization_id, localization_code, name, slug, created_at, updated_at)
            VALUES (?, 1, 'en', ?, ?, NOW(), NOW())
        ");
        $loc_slug = generateSlug($mapping['name_en'] . '-en');
        $stmt->execute([$book_id, $mapping['name_en'], $loc_slug]);
        
        return $book_id;
        
    } catch (PDOException $e) {
        echo "❌ Error creating book: " . $e->getMessage() . "\n";
        return null;
    }
}

function processHadiths($pdo, $book_id, $hadiths, $language_code, $edition_code, $update_existing) {
    $hadith_count = 0;
    $updated_count = 0;
    $skipped_count = 0;
    $translation_count = 0;
    
    echo "   📜 Processing " . count($hadiths) . " hadiths...\n";
    
    // Get all chapters for this book
    $stmt = $pdo->prepare("SELECT id FROM chapters WHERE book_id = ? ORDER BY chapter_no LIMIT 1");
    $stmt->execute([$book_id]);
    $chapter = $stmt->fetch();
    $chapter_id = $chapter['id'] ?? 1;
    
    $processed = 0;
    $total_to_process = count($hadiths);
    
    foreach ($hadiths as $index => $hadith_data) {
        $processed++;
        
        if (!is_array($hadith_data)) {
            continue;
        }
        
        $hadith_number = $hadith_data['hadithnumber'] ?? null;
        $arabic_text = $hadith_data['text'] ?? '';
        $grades = $hadith_data['grades'] ?? [];
        
        if (!$hadith_number) {
            continue;
        }
        
        // Show progress every 100 hadiths
        if ($processed % 100 === 0) {
            $percent = round(($processed / $total_to_process) * 100, 1);
            echo "     📊 Progress: $processed/$total_to_process ($percent%)\n";
        }
        
        // Get grade
        $grade_text = '';
        if (is_array($grades) && isset($grades[0]['grade'])) {
            $grade_text = $grades[0]['grade'];
        }
        
        // Check if exists
        $stmt = $pdo->prepare("
            SELECT id, arabic_text as existing_text, grade as existing_grade 
            FROM hadiths 
            WHERE book_id = ? AND hadith_number = ?
        ");
        $stmt->execute([$book_id, $hadith_number]);
        $existing = $stmt->fetch();
        
        if ($existing) {
            // Hadith already exists
            $hadith_id = $existing['id'];
            $existing_text = $existing['existing_text'] ?? '';
            $existing_grade = $existing['existing_grade'] ?? '';
            
            // Check if we should update
            $should_update = false;
            $update_reason = '';
            
            if ($update_existing) {
                // Update if API has text but database doesn't
                if (!empty($arabic_text) && empty($existing_text)) {
                    $should_update = true;
                    $update_reason = 'Adding missing Arabic text';
                }
                // Update if API has better grade information
                elseif (!empty($grade_text) && (empty($existing_grade) || $grade_text !== $existing_grade)) {
                    $should_update = true;
                    $update_reason = 'Updating grade information';
                }
                // Update if API text is longer/more complete
                elseif (!empty($arabic_text) && strlen($arabic_text) > strlen($existing_text)) {
                    $should_update = true;
                    $update_reason = 'Updating with more complete text';
                }
            }
            
            if ($should_update) {
                // Update existing hadith
                $stmt = $pdo->prepare("
                    UPDATE hadiths 
                    SET arabic_text = ?, grade = ?, updated_at = NOW()
                    WHERE id = ?
                ");
                $stmt->execute([$arabic_text, $grade_text, $hadith_id]);
                $updated_count++;
                
                // Show update info for first few updates
                if ($updated_count <= 5) {
                    echo "     🔄 Updated hadith $hadith_number: $update_reason\n";
                }
            } else {
                $skipped_count++;
            }
            
        } else {
            // Insert new hadith (only if it has text)
            if (!empty($arabic_text)) {
                try {
                    $stmt = $pdo->prepare("
                        INSERT INTO hadiths (book_id, chapter_id, hadith_number, arabic_text, grade, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, NOW(), NOW())
                    ");
                    $stmt->execute([$book_id, $chapter_id, $hadith_number, $arabic_text, $grade_text]);
                    
                    $hadith_id = $pdo->lastInsertId();
                    $hadith_count++;
                    
                    // Show new hadith info for first few
                    if ($hadith_count <= 5) {
                        echo "     📥 New hadith $hadith_number inserted\n";
                    }
                    
                } catch (PDOException $e) {
                    if ($e->getCode() != 23000) {
                        // Only show error if not a duplicate key
                        echo "     ❌ Error inserting hadith $hadith_number: " . $e->getMessage() . "\n";
                    }
                    continue;
                }
            } else {
                // Skip hadiths with empty text
                continue;
            }
        }
        
        // Handle translation (for non-Arabic editions)
        if ($language_code !== 'ar' && !empty($arabic_text)) {
            $translation_count += handleTranslation($pdo, $hadith_id, $language_code, $arabic_text, $update_existing);
        }
    }
    
    // Show final summary
    echo "   ✅ Processing complete:\n";
    echo "     📥 New hadiths: $hadith_count\n";
    echo "     🔄 Updated hadiths: $updated_count\n";
    echo "     ⏭️  Skipped: $skipped_count\n";
    echo "     🌐 Translations: $translation_count\n";
    
    return [
        'hadiths' => $hadith_count, 
        'updated' => $updated_count,
        'skipped' => $skipped_count,
        'translations' => $translation_count
    ];
}

function handleTranslation($pdo, $hadith_id, $language_code, $text, $update_existing) {
    // Check if translation exists
    $stmt = $pdo->prepare("
        SELECT id, translation_text as existing_text 
        FROM hadith_translations 
        WHERE hadith_id = ? AND localization_code = ?
    ");
    $stmt->execute([$hadith_id, $language_code]);
    $existing = $stmt->fetch();
    
    if ($existing) {
        // Translation exists
        if ($update_existing) {
            $existing_text = $existing['existing_text'] ?? '';
            // Update if new text is longer/more complete
            if (strlen($text) > strlen($existing_text)) {
                $stmt = $pdo->prepare("
                    UPDATE hadith_translations 
                    SET translation_text = ?, updated_at = NOW()
                    WHERE id = ?
                ");
                $stmt->execute([$text, $existing['id']]);
                return 1; // Count as updated translation
            }
        }
        return 0; // No update needed
    } else {
        // Insert new translation
        try {
            $stmt = $pdo->prepare("
                INSERT INTO hadith_translations (hadith_id, localization_id, localization_code, translation_text, created_at, updated_at)
                VALUES (?, 1, ?, ?, NOW(), NOW())
            ");
            $stmt->execute([$hadith_id, $language_code, $text]);
            return 1; // Count as new translation
        } catch (PDOException $e) {
            return 0;
        }
    }
}

// 2. Import from HadeethEnc
function importFromHadeethEnc($pdo, $update_existing = true) {
    global $hadeethenc_base_url;
    
    echo "\n📚 Starting HadeethEnc import...\n";
    if ($update_existing) {
        echo "⚡ Mode: INSERT new hadiths and UPDATE existing ones\n";
    } else {
        echo "⚡ Mode: INSERT new hadiths only (skip existing)\n";
    }
    
    // Get or create HadeethEnc book
    $book_id = getOrCreateHadeethEncBook($pdo);
    if (!$book_id) {
        return;
    }
    
    // Get or create default chapter
    $chapter_id = getOrCreateDefaultChapter($pdo, $book_id);
    if (!$chapter_id) {
        return;
    }
    
    // First, get categories
    $categories = getHadeethEncCategories($pdo);
    if (empty($categories)) {
        echo "❌ No categories found\n";
        return;
    }
    
    echo "📂 Found " . count($categories) . " categories\n";
    
    $total_hadiths = 0;
    $total_updated = 0;
    $categories_processed = 0;
    
    foreach ($categories as $category_id => $category_name) {
        $categories_processed++;
        
        // Limit to 5 categories for testing, remove this limit for full import
        if ($categories_processed > 5) {
            echo "\n⚠️  Limiting to 5 categories for testing. Remove this limit for full import.\n";
            break;
        }
        
        echo "\n📂 Category $categories_processed: $category_name (ID: $category_id)\n";
        
        $page = 1;
        $has_more = true;
        $category_hadiths = 0;
        $category_updated = 0;
        
        while ($has_more && $page <= 2) { // Limit to 2 pages per category for testing
            $url = $hadeethenc_base_url . "/hadeeths/list/?language=en&category_id=$category_id&page=$page&per_page=20";
            
            $response = fetchData($url);
            
            if (!$response || !isset($response['data'])) {
                break;
            }
            
            $hadiths_list = $response['data'];
            if (empty($hadiths_list)) {
                break;
            }
            
            echo "   📄 Page $page: " . count($hadiths_list) . " hadiths\n";
            
            foreach ($hadiths_list as $hadith_basic) {
                $hadith_id = $hadith_basic['id'] ?? null;
                $title = $hadith_basic['title'] ?? '';
                
                if (!$hadith_id) {
                    continue;
                }
                
                // Fetch details
                $details_url = $hadeethenc_base_url . "/hadeeths/one/?language=en&id=$hadith_id";
                $hadith_details = fetchData($details_url);
                
                if (!$hadith_details) {
                    continue;
                }
                
                // Import hadith
                $result = importHadeethEncHadith($pdo, $hadith_details, $book_id, $chapter_id, $category_id, $title, $update_existing);
                if ($result['imported']) {
                    $total_hadiths++;
                    $category_hadiths++;
                }
                if ($result['updated']) {
                    $total_updated++;
                    $category_updated++;
                }
                
                usleep(50000); // 0.05 second delay
            }
            
            // Check for more pages
            $meta = $response['meta'] ?? [];
            $has_more = isset($meta['last_page']) && $page < (int)$meta['last_page'];
            $page++;
            
            sleep(1); // Delay between pages
        }
        
        echo "   ✅ Category completed: $category_hadiths new, $category_updated updated\n";
    }
    
    echo "\n✅ HadeethEnc import completed:\n";
    echo "   📥 New hadiths: $total_hadiths\n";
    echo "   🔄 Updated hadiths: $total_updated\n";
}

function getHadeethEncCategories($pdo, $language = 'en') {
    global $hadeethenc_base_url;
    
    $url = $hadeethenc_base_url . "/categories/roots/?language=$language";
    $categories_data = fetchData($url);
    
    if (!$categories_data || !is_array($categories_data)) {
        return [];
    }
    
    $categories = [];
    
    foreach ($categories_data as $category) {
        $category_id = $category['id'] ?? null;
        $title = $category['title'] ?? '';
        
        if (!$category_id || !$title) {
            continue;
        }
        
        // Check if exists in database
        $stmt = $pdo->prepare("SELECT id FROM categories WHERE id = ?");
        $stmt->execute([$category_id]);
        $existing = $stmt->fetch();
        
        if (!$existing) {
            // Insert category
            $slug = generateSlug($title);
            try {
                $stmt = $pdo->prepare("
                    INSERT INTO categories (id, parent_id, name_en, name_ar, slug, created_at, updated_at)
                    VALUES (?, NULL, ?, NULL, ?, NOW(), NOW())
                ");
                $stmt->execute([$category_id, $title, $slug]);
                
                // Insert localization
                $stmt = $pdo->prepare("
                    INSERT INTO category_localizations (category_id, localization_code, name, slug, created_at, updated_at)
                    VALUES (?, ?, ?, ?, NOW(), NOW())
                ");
                $stmt->execute([$category_id, $language, $title, $slug]);
                
            } catch (PDOException $e) {
                // Ignore duplicates
            }
        }
        
        $categories[$category_id] = $title;
    }
    
    return $categories;
}

function getOrCreateHadeethEncBook($pdo) {
    $stmt = $pdo->prepare("SELECT id FROM books WHERE code = 'hadeethenc'");
    $stmt->execute();
    $existing = $stmt->fetch();
    
    if ($existing) {
        return $existing['id'];
    }
    
    try {
        $stmt = $pdo->prepare("
            INSERT INTO books (code, name_en, name_ar, total_hadith, slug, created_at, updated_at)
            VALUES ('hadeethenc', 'HadeethEnc Collection', 'مجموعة الحديث', 0, 'hadeethenc-collection', NOW(), NOW())
        ");
        $stmt->execute();
        
        $book_id = $pdo->lastInsertId();
        
        // Add localization
        $stmt = $pdo->prepare("
            INSERT INTO books_localizations (book_id, localization_id, localization_code, name, slug, created_at, updated_at)
            VALUES (?, 1, 'en', 'HadeethEnc Collection', 'hadeethenc-collection-en', NOW(), NOW())
        ");
        $stmt->execute([$book_id]);
        
        return $book_id;
        
    } catch (PDOException $e) {
        echo "❌ Error creating HadeethEnc book: " . $e->getMessage() . "\n";
        return null;
    }
}

function getOrCreateDefaultChapter($pdo, $book_id) {
    $stmt = $pdo->prepare("SELECT id FROM chapters WHERE book_id = ? AND chapter_no = 1");
    $stmt->execute([$book_id]);
    $existing = $stmt->fetch();
    
    if ($existing) {
        return $existing['id'];
    }
    
    try {
        $stmt = $pdo->prepare("
            INSERT INTO chapters (book_id, chapter_no, name_en, name_ar, total_hadith, slug, created_at, updated_at)
            VALUES (?, 1, 'General Hadith', 'أحاديث عامة', 0, 'general-hadith', NOW(), NOW())
        ");
        $stmt->execute([$book_id]);
        
        $chapter_id = $pdo->lastInsertId();
        
        // Add localization
        $stmt = $pdo->prepare("
            INSERT INTO chapters_localizations (chapter_id, localization_id, localization_code, name, slug, created_at, updated_at)
            VALUES (?, 1, 'en', 'General Hadith', 'general-hadith-en', NOW(), NOW())
        ");
        $stmt->execute([$chapter_id]);
        
        return $chapter_id;
        
    } catch (PDOException $e) {
        echo "❌ Error creating default chapter: " . $e->getMessage() . "\n";
        return null;
    }
}

function importHadeethEncHadith($pdo, $hadith_detail, $book_id, $chapter_id, $category_id, $title, $update_existing) {
    $hadith_id = $hadith_detail['id'] ?? null;
    $hadeeth_text = $hadith_detail['hadeeth'] ?? '';
    $attribution = $hadith_detail['attribution'] ?? '';
    $grade = $hadith_detail['grade'] ?? '';
    $explanation = $hadith_detail['explanation'] ?? '';
    $hints = $hadith_detail['hints'] ?? [];
    
    if (!$hadith_id || empty($hadeeth_text)) {
        return ['imported' => false, 'updated' => false];
    }
    
    // Check if exists (using HadeethEnc ID as hadith_number)
    $stmt = $pdo->prepare("
        SELECT id, arabic_text as existing_text, grade as existing_grade 
        FROM hadiths 
        WHERE book_id = ? AND hadith_number = ?
    ");
    $stmt->execute([$book_id, $hadith_id]);
    $existing = $stmt->fetch();
    
    if ($existing) {
        // Hadith exists
        $hadith_db_id = $existing['id'];
        $existing_text = $existing['existing_text'] ?? '';
        $existing_grade = $existing['existing_grade'] ?? '';
        
        $updated = false;
        
        if ($update_existing) {
            // Update if needed
            if (empty($existing_text) || strlen($hadeeth_text) > strlen($existing_text)) {
                $stmt = $pdo->prepare("
                    UPDATE hadiths 
                    SET arabic_text = ?, grade = ?, attribution_ar = ?, updated_at = NOW()
                    WHERE id = ?
                ");
                $stmt->execute([$hadeeth_text, $grade, $attribution, $hadith_db_id]);
                $updated = true;
            }
        }
        
        // Always update category link
        try {
            $stmt = $pdo->prepare("INSERT IGNORE INTO hadith_category (hadith_id, category_id) VALUES (?, ?)");
            $stmt->execute([$hadith_db_id, $category_id]);
        } catch (PDOException $e) {
            // Ignore
        }
        
        return ['imported' => false, 'updated' => $updated];
        
    } else {
        // Insert new hadith
        try {
            $stmt = $pdo->prepare("
                INSERT INTO hadiths (book_id, chapter_id, hadith_number, arabic_text, grade, 
                    attribution_ar, categories, available_translations, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW(), NOW())
            ");
            
            $categories_json = json_encode([(int)$category_id]);
            $translations_json = json_encode(['en']);
            
            $stmt->execute([
                $book_id, 
                $chapter_id, 
                $hadith_id,
                $hadeeth_text, 
                $grade,
                $attribution,
                $categories_json,
                $translations_json
            ]);
            
            $hadith_db_id = $pdo->lastInsertId();
            
            // Link to category
            try {
                $stmt = $pdo->prepare("INSERT IGNORE INTO hadith_category (hadith_id, category_id) VALUES (?, ?)");
                $stmt->execute([$hadith_db_id, $category_id]);
            } catch (PDOException $e) {
                // Ignore
            }
            
            // Add English translation
            try {
                $stmt = $pdo->prepare("
                    INSERT INTO hadith_translations (hadith_id, localization_id, localization_code, translation_text, 
                        hadeeth_intro, attribution, created_at, updated_at)
                    VALUES (?, 1, 'en', ?, ?, ?, NOW(), NOW())
                ");
                
                $hints_text = is_array($hints) ? implode("\n", $hints) : $hints;
                $stmt->execute([$hadith_db_id, $title, $explanation, $hints_text]);
                
            } catch (PDOException $e) {
                // Ignore
            }
            
            return ['imported' => true, 'updated' => false];
            
        } catch (PDOException $e) {
            if ($e->getCode() == 23000) {
                return ['imported' => false, 'updated' => false]; // Duplicate
            }
            return ['imported' => false, 'updated' => false];
        }
    }
}

// 3. Update statistics
function updateAllStatistics($pdo) {
    echo "\n📊 Updating statistics...\n";
    
    // Update book totals
    $stmt = $pdo->prepare("
        UPDATE books b
        SET b.total_hadith = (
            SELECT COUNT(*) FROM hadiths h WHERE h.book_id = b.id
        ), b.updated_at = NOW()
    ");
    $stmt->execute();
    echo "✅ Book statistics updated\n";
    
    // Update chapter totals
    $stmt = $pdo->prepare("
        UPDATE chapters c
        SET c.total_hadith = (
            SELECT COUNT(*) FROM hadiths h WHERE h.chapter_id = c.id
        ), c.updated_at = NOW()
    ");
    $stmt->execute();
    echo "✅ Chapter statistics updated\n";
    
    // Show summary
    showStatistics($pdo);
}

function showStatistics($pdo) {
    echo "\n📈 CURRENT STATISTICS\n";
    echo "=====================\n";
    
    // Books
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM books");
    $books = $stmt->fetch();
    echo "📚 Books: " . ($books['count'] ?? 0) . "\n";
    
    // Chapters
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM chapters");
    $chapters = $stmt->fetch();
    echo "📖 Chapters: " . ($chapters['count'] ?? 0) . "\n";
    
    // Categories
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM categories");
    $categories = $stmt->fetch();
    echo "📂 Categories: " . ($categories['count'] ?? 0) . "\n";
    
    // Hadiths
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM hadiths");
    $hadiths = $stmt->fetch();
    echo "📜 Hadiths: " . ($hadiths['count'] ?? 0) . "\n";
    
    // Translations
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM hadith_translations");
    $translations = $stmt->fetch();
    echo "🌐 Translations: " . ($translations['count'] ?? 0) . "\n";
    
    // Books with counts
    echo "\n📊 Books with hadith counts:\n";
    $stmt = $pdo->query("
        SELECT b.code, b.name_en, b.total_hadith 
        FROM books b 
        ORDER BY b.total_hadith DESC
    ");
    $books_list = $stmt->fetchAll();
    
    foreach ($books_list as $book) {
        echo "   {$book['name_en']} ({$book['code']}): {$book['total_hadith']} hadiths\n";
    }
}

// Main function
function main() {
    global $pdo;
    
    echo "🚀 Starting Hadith Data Import\n";
    echo "===============================\n";
    
    try {
        // Check current statistics before import
        showStatistics($pdo);
        
        // Ask for import mode
        echo "\n📋 Import Mode:\n";
        echo "1. Insert new hadiths only (skip existing)\n";
        echo "2. Insert new and update existing hadiths\n";
        echo "Enter mode choice (1-2): ";
        
        $handle = fopen("php://stdin", "r");
        $mode_choice = trim(fgets($handle));
        fclose($handle);
        
        $update_existing = ($mode_choice == '2');
        
        // Choose which sources to import
        echo "\n📚 Choose import sources:\n";
        echo "1. Import from fawazahmed0 API\n";
        echo "2. Import from HadeethEnc API\n";
        echo "3. Run all imports\n";
        echo "Enter source choice (1-3): ";
        
        $handle = fopen("php://stdin", "r");
        $source_choice = trim(fgets($handle));
        fclose($handle);
        
        switch ($source_choice) {
            case '1':
                importFromFawazahmed0($pdo, $update_existing);
                break;
                
            case '2':
                importFromHadeethEnc($pdo, $update_existing);
                break;
                
            case '3':
                importFromFawazahmed0($pdo, $update_existing);
                importFromHadeethEnc($pdo, $update_existing);
                break;
                
            default:
                echo "Invalid choice. Running fawazahmed0 import only.\n";
                importFromFawazahmed0($pdo, $update_existing);
                break;
        }
        
        // Update statistics
        updateAllStatistics($pdo);
        
        echo "\n🎉 Import completed successfully!\n";
        
    } catch (Exception $e) {
        echo "\n❌ Error: " . $e->getMessage() . "\n";
    }
}

// Run the import
main();