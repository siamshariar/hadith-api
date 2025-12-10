<?php
/**
 * Report missing hadith translations for a given language
 * Usage: php scripts/report_missing_translations.php --lang=en --output=missing_en.json --limit=1000
 */

require __DIR__ . '/../vendor/autoload.php';
$app = require __DIR__ . '/../bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

$options = [];
foreach ($argv as $arg) {
    if (Str::startsWith($arg, '--')) {
        $parts = explode('=', $arg, 2);
        $key = ltrim($parts[0], '-');
        $options[$key] = $parts[1] ?? true;
    }
}

$lang = $options['lang'] ?? null;
$output = $options['output'] ?? null;
$limit = isset($options['limit']) ? (int)$options['limit'] : null;

if (!$lang) {
    echo "Usage: php scripts/report_missing_translations.php --lang=en [--output=missing_en.json] [--limit=1000]\n";
    exit(1);
}

// Find hadith IDs that do not have a translation for $lang
$query = DB::table('hadiths')
    ->leftJoin('hadith_translations', function($join) use ($lang) {
        $join->on('hadiths.id', '=', 'hadith_translations.hadith_id')
            ->where('hadith_translations.localization_code', '=', $lang);
    })
    ->whereNull('hadith_translations.id')
    ->select('hadiths.id as hadith_id', 'hadiths.book_id', 'hadiths.chapter_id')
    ->orderBy('hadiths.id');

if ($limit) {
    $query->limit($limit);
}

$rows = $query->get();

$ids = [];
foreach ($rows as $r) {
    $ids[] = (int)$r->hadith_id;
}

$report = [
    'language' => $lang,
    'missing_count' => count($ids),
    'hadith_ids' => $ids,
    'sample' => array_slice($ids, 0, 10),
];

if ($output) {
    file_put_contents($output, json_encode($report, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    echo "Wrote report to {$output}\n";
}

echo "Missing translations for language {$lang}: {$report['missing_count']} hadiths (sample: ".json_encode($report['sample']).")\n";

?>