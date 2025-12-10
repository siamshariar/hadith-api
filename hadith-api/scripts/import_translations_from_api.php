<?php
/**
 * Import translations from an external API into `hadith_translations` table.
 * Usage (from project root):
 * php scripts/import_translations_from_api.php --base="https://source.example/api" --lang=bn --start=1 --end=1000
 * Options:
 * --base  : Base URL of the source API that returns translation for a hadith id, e.g. /hadiths/{id}/translations/{lang}
 * --lang  : language code to import (e.g. bn, en, ar)
 * --start : starting hadith id
 * --end   : ending hadith id
 * --ids   : optional comma separated list of specific hadith ids to import
 *
 * The script will upsert into hadith_translations: hadith_id, localization_code, translation_text, explanation, hints
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

$base = $options['base'] ?? null;
$lang = $options['lang'] ?? null;
$start = isset($options['start']) ? (int)$options['start'] : null;
$end = isset($options['end']) ? (int)$options['end'] : null;
$idsList = isset($options['ids']) ? explode(',', $options['ids']) : null;

if (!$base || !$lang || (!($start && $end) && !$idsList && !isset($options['missing']))) {
    echo "Usage: php scripts/import_translations_from_api.php --base=BASE_URL --lang=LANG [--start=N --end=M | --ids=1,2,3 | --missing=true] [--limit=1000]\n";
    echo "Examples:\n";
    echo "  php scripts/import_translations_from_api.php --base='https://source.example/api' --lang=bn --start=1 --end=100\n";
    echo "  php scripts/import_translations_from_api.php --base='https://source.example/api' --lang=en --ids=16522,24080\n";
    echo "  php scripts/import_translations_from_api.php --base='https://source.example/api' --lang=bn --missing=true --limit=500\n";
    exit(1);
}

$client = new \GuzzleHttp\Client(['base_uri' => rtrim($base, '/') . '/','timeout' => 10.0]);

// If missing=true, compute list of hadith IDs that are missing translations for this language
$ids = [];
$missing = isset($options['missing']) && ($options['missing'] === 'true' || $options['missing'] === true);
if ($missing) {
    // Query hadiths that do not have a translation for $lang
    $q = DB::table('hadiths')
        ->leftJoin('hadith_translations', function($join) use ($lang) {
            $join->on('hadiths.id', '=', 'hadith_translations.hadith_id')
                ->where('hadith_translations.localization_code', '=', $lang);
        })
        ->whereNull('hadith_translations.id')
        ->select('hadiths.id');

    if ($start && $end) {
        $q->whereBetween('hadiths.id', [$start, $end]);
    }
    if (isset($options['limit'])) {
        $q->limit((int)$options['limit']);
    }

    $rows = $q->get();
    foreach ($rows as $r) { $ids[] = (int)$r->id; }

} else {
    if ($idsList) {
        foreach ($idsList as $i) { $ids[] = (int)trim($i); }
    } else {
        for ($i = $start; $i <= $end; $i++) $ids[] = $i;
    }
}

// Deduplicate IDs to avoid repeated requests
$ids = array_values(array_unique($ids));

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
if (empty($ids)) {
    echo "No IDs to process. Exiting.\n";
    exit(0);
}

foreach ($ids as $id) {
    try {
        // Assume source endpoint: /hadiths/{id}/translations/{lang} returning JSON { translation_text, explanation, hints }
        $path = "hadiths/{$id}/translations/{$lang}";
        $res = $client->get($path);
        if ($res->getStatusCode() !== 200) {
            echo "Hadith {$id}: no translation (HTTP {$res->getStatusCode()})\n";
            continue;
        }

        $body = (string)$res->getBody();
        $json = json_decode($body, true);
        if (!$json) {
            echo "Hadith {$id}: invalid JSON\n";
            continue;
        }

        // Normalize response fields
        $translation_text = $json['translation_text'] ?? $json['translation'] ?? null;
        $explanation = $json['explanation'] ?? null;
        $hints = $json['hints'] ?? null;

        // Try to resolve hadith id if translation is not present for that hadith id but response includes book + hadith_number
        if (!$translation_text) {
            echo "Hadith {$id}: no translation_text field\n";
            continue;
        }

        // Upsert into DB
        $existing = DB::table('hadith_translations')
            ->where('hadith_id', $id)
            ->where('localization_code', $lang)
            ->first();

        $data = [
            'hadith_id' => $id,
            'localization_code' => $lang,
            'translation_text' => $translation_text,
            'explanation' => $explanation,
            'hints' => is_array($hints) ? json_encode($hints, JSON_UNESCAPED_UNICODE) : $hints,
            'updated_at' => date('Y-m-d H:i:s'),
        ];

        // If the hadith id does not exist in our DB, attempt to resolve by book code and hadith_number returned by the remote response
        $hadithExists = DB::table('hadiths')->where('id', $id)->exists();
        if (!$hadithExists && isset($json['book']) && isset($json['hadith_number'])) {
            $bookCode = $json['book']['code'] ?? ($json['book']['slug'] ?? null);
            if ($bookCode) {
                $book = DB::table('books')->where('code', $bookCode)->orWhere('slug', $bookCode)->first();
                if ($book) {
                    $found = DB::table('hadiths')->where('book_id', $book->id)->where('hadith_number', $json['hadith_number'])->first();
                    if ($found) {
                        $id = $found->id;
                        $existing = DB::table('hadith_translations')->where('hadith_id', $id)->where('localization_code', $lang)->first();
                    }
                }
            }
        }

        if ($existing) {
            DB::table('hadith_translations')->where('id', $existing->id)->update($data);
            echo "Hadith {$id}: updated\n";
        } else {
            $data['created_at'] = date('Y-m-d H:i:s');
            // Only set localization_id if mapping exists to avoid FK failures
            if (!empty($localizationId) && $localizationId > 0) {
                $data['localization_id'] = $localizationId;
            }
            DB::table('hadith_translations')->insert($data);
            echo "Hadith {$id}: inserted\n";
        }

        // Also ensure language_code alias exists (if migration added it)
        if (Schema::hasColumn('hadith_translations', 'language_code')) {
            DB::table('hadith_translations')->where('hadith_id', $id)->where('localization_code', $lang)
                ->update(['language_code' => $lang]);
        }

        $counter++;
        // small sleep to avoid hammering
        usleep(200000);

    } catch (\GuzzleHttp\Exception\RequestException $e) {
        echo "Hadith {$id}: request failed - " . $e->getMessage() . "\n";
    } catch (\Exception $e) {
        echo "Hadith {$id}: error - " . $e->getMessage() . "\n";
    }
}

echo "Done. Processed {$counter} items.\n";

?>