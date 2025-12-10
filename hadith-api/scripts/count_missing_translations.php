<?php
require __DIR__ . '/../vendor/autoload.php';
$app = require __DIR__ . '/../bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

use Illuminate\Support\Facades\DB;

$lang = $argv[1] ?? 'bn';

echo "Counting missing translations for language: $lang\n";

$count = DB::table('hadiths')
    ->leftJoin('hadith_translations', function($join) use ($lang) {
        $join->on('hadiths.id', '=', 'hadith_translations.hadith_id')
            ->where('hadith_translations.localization_code', '=', $lang);
    })
    ->whereNull('hadith_translations.id')
    ->count();

echo "Missing translations: {$count}\n";

?>