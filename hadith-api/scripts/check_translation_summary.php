<?php
/**
 * Check counts of translations per localization code
 * Usage: php scripts/check_translation_summary.php --lang=bn
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
        [$k, $v] = array_pad(explode('=', $arg, 2), 2, true);
        $options[ltrim($k, '-')] = $v === true ? true : $v;
    }
}

$lang = $options['lang'] ?? null;

if ($lang) {
    $count = DB::table('hadith_translations')->where('localization_code', $lang)->count();
    echo "Translations for {$lang}: {$count}\n";
    exit(0);
}

$rows = DB::table('hadith_translations')
    ->select('localization_code', DB::raw('COUNT(*) as cnt'))
    ->groupBy('localization_code')
    ->orderBy('cnt', 'desc')
    ->get();

foreach ($rows as $r) {
    echo "{$r->localization_code}: {$r->cnt}\n";
}

?>