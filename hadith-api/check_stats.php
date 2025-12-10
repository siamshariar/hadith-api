<?php
require_once 'vendor/autoload.php';

$app = require_once 'bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

use Illuminate\Support\Facades\DB;

echo "Hadiths per book:" . PHP_EOL;
$hadiths_per_book = DB::table('hadiths')
    ->select('books.code', DB::raw('COUNT(*) as count'))
    ->join('books', 'hadiths.book_id', '=', 'books.id')
    ->groupBy('books.code')
    ->get();

foreach($hadiths_per_book as $row) {
    echo $row->code . ': ' . $row->count . PHP_EOL;
}

echo PHP_EOL . "Translations per language:" . PHP_EOL;
$translations_per_lang = DB::table('hadith_translations')
    ->select('localization_code', DB::raw('COUNT(*) as count'))
    ->groupBy('localization_code')
    ->get();

foreach($translations_per_lang as $row) {
    echo $row->localization_code . ': ' . $row->count . PHP_EOL;
}
?>