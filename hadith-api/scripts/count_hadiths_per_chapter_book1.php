<?php
require __DIR__ . '/../vendor/autoload.php';
$app = require __DIR__ . '/../bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

use Illuminate\Support\Facades\DB;

$rows = DB::table('hadiths')
    ->select('chapter_id', DB::raw('COUNT(*) as cnt'))
    ->where('book_id', 1)
    ->groupBy('chapter_id')
    ->orderBy('chapter_id')
    ->get();

foreach ($rows as $r) {
    echo 'chapter:'.$r->chapter_id.' cnt:'.$r->cnt.PHP_EOL;
}
?>