<?php
/**
 * Import translations from a local JSON file containing translations (e.g., test_bengali_output.json)
 * Usage: php scripts/import_translations_from_file.php --file=test_bengali_output.json --lang=bn [--limit=1000]
 */

require __DIR__ . '/../vendor/autoload.php';
$app = require __DIR__ . '/../bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Str;

$options = [];
foreach ($argv as $arg) {
    if (Str::startsWith($arg, '--')) {
        $parts = explode('=', $arg, 2);
        $key = ltrim($parts[0], '-');
        $options[$key] = $parts[1] ?? true;
    }
}

$file = $options['file'] ?? null;
$lang = $options['lang'] ?? null;
$limit = isset($options['limit']) ? (int)$options['limit'] : null;

if (!$file || !$lang) {
    echo "Usage: php scripts/import_translations_from_file.php --file=path.json --lang=bn [--limit=1000]\n";
    exit(1);
}

$path = realpath($file);
if (!$path || !file_exists($path)) {
    echo "File not found: {$file}\n";
    exit(1);
}

$contents = file_get_contents($path);
$data = json_decode($contents, true);
if (!$data) {
    echo "Invalid JSON file: {$file}\n";
    exit(1);
}

$translations = [];

// Recursively search for hadith nodes with id and translation
$stack = [$data];
while ($stack) {
    $node = array_pop($stack);
    if (is_array($node)) {
        if (isset($node['id']) && isset($node['translation']) && is_array($node['translation'])) {
            $translations[] = [
                'hadith_id' => (int)$node['id'],
                'translation' => $node['translation'],
                'hadith_node' => $node
            ];
        }
        foreach ($node as $child) {
            if (is_array($child)) $stack[] = $child;
        }
    }
}

if ($limit) {
    $translations = array_slice($translations, 0, $limit);
}

$counter = 0;
// Map language code to numeric localization_id (fallbacks)
$langToId = [
    'en' => 1,
    'ar' => 2,
    'bn' => 3,
    'ur' => 4,
    'tr' => 5,
    'fr' => 6,
    'es' => 7,
    'id' => 8,
    'ms' => 9
];
$localizationId = $langToId[$lang] ?? 0;
foreach ($translations as $t) {
    $id = $t['hadith_id'];
    // If the JSON node didn't provide a valid hadith id or it isn't in the DB, try resolving by book/number
    if (!DB::table('hadiths')->where('id', $id)->exists()) {
        // Check if the node includes a 'book' object and hadith number
        $node = $t['hadith_node'] ?? null; // not present unless we included original node
        if (is_array($node) && isset($node['book']) && isset($node['hadith_number'])) {
            $bookCode = $node['book']['code'] ?? ($node['book']['slug'] ?? null);
            $number = $node['hadith_number'];
            if ($bookCode) {
                $book = DB::table('books')->where('code', $bookCode)->orWhere('slug', $bookCode)->first();
                if ($book) {
                    $found = DB::table('hadiths')->where('book_id', $book->id)->where('hadith_number', $number)->first();
                    if ($found) {
                        $id = $found->id;
                    }
                }
            }
        }
    }
    $trans = $t['translation'];
    $text = $trans['translation_text'] ?? null;
    $explanation = $trans['explanation'] ?? null;
    $hints = $trans['hints'] ?? null;
    if (!$text) continue;

    // Skip if hadith id doesn't exist in our DB (avoid FK constraint errors)
    $hadithExists = $id && DB::table('hadiths')->where('id', $id)->exists();
    if (!$hadithExists) {
        echo "Hadith {$id}: not found in DB, skipping\n";
        continue;
    }

    $existing = DB::table('hadith_translations')->where('hadith_id', $id)->where('localization_code', $lang)->first();
        $data = [
        'hadith_id' => $id,
        'localization_code' => $lang,
        'translation_text' => $text,
        'explanation' => $explanation,
        'hints' => is_array($hints) ? json_encode($hints, JSON_UNESCAPED_UNICODE) : $hints,
        'updated_at' => date('Y-m-d H:i:s')
    ];

    if ($existing) {
        DB::table('hadith_translations')->where('id', $existing->id)->update($data);
        echo "Hadith {$id}: updated\n";
    } else {
        $data['created_at'] = date('Y-m-d H:i:s');
        // Only set localization_id if we have a mapping (avoid FK constraint issues)
        if (!empty($localizationId) && $localizationId > 0) {
            $data['localization_id'] = $localizationId;
        }
        DB::table('hadith_translations')->insert($data);
        echo "Hadith {$id}: inserted\n";
    }

    // Ensure alias exists
    if (Schema::hasColumn('hadith_translations', 'language_code')) {
        DB::table('hadith_translations')->where('hadith_id', $id)->where('localization_code', $lang)
            ->update(['language_code' => $lang]);
    }

    $counter++;
}

echo "Done. Processed {$counter} items.\n";

?>