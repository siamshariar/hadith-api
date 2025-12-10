<?php
require_once 'vendor/autoload.php';

$app = require_once 'bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

use Illuminate\Support\Facades\DB;

echo "Languages in translations: " . PHP_EOL;
$languages = DB::table('hadith_translations')->select('localization_code')->distinct()->get()->pluck('localization_code')->toArray();
print_r($languages);

echo PHP_EOL . "Books in database: " . PHP_EOL;
$books = DB::table('books')->select('code', 'name_en')->get();
foreach($books as $book) {
    echo $book->code . ': ' . $book->name_en . PHP_EOL;
}

echo PHP_EOL . "Sample hadith with translations: " . PHP_EOL;
$sample = DB::table('hadiths')->where('id', 1)->first();
if($sample) {
    echo "Hadith ID 1 Arabic: " . substr($sample->arabic_text, 0, 100) . '...' . PHP_EOL;
    $translations = DB::table('hadith_translations')->where('hadith_id', 1)->get();
    echo "Translations count: " . $translations->count() . PHP_EOL;
    foreach($translations as $trans) {
        echo $trans->localization_code . ': ' . substr($trans->translation_text, 0, 50) . '...' . PHP_EOL;
    }
}
?>