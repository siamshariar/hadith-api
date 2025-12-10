<?php
require_once 'vendor/autoload.php';

$app = require_once 'bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

use Illuminate\Support\Facades\DB;

echo "Bukhari hadith numbers (first 10):" . PHP_EOL;
$hadiths = DB::table('hadiths')->where('book_id', 1)->select('id', 'hadith_number', 'chapter_id')->limit(10)->get();
foreach($hadiths as $h) {
    echo "ID {$h->id}: hadith_number = '{$h->hadith_number}', chapter_id = {$h->chapter_id}" . PHP_EOL;
}

echo PHP_EOL . "Translations for first hadith:" . PHP_EOL;
$translations = DB::table('hadith_translations')->where('hadith_id', 1)->select('localization_code')->get();
foreach($translations as $t) {
    echo $t->localization_code . PHP_EOL;
}
?>