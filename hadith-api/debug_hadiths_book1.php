<?php
$url = 'http://127.0.0.1:8000/api/hadiths?per_page=200&page=1';
$r = @file_get_contents($url);
if (!$r) { echo "NO RESPONSE\n"; exit(1);} 
$d = json_decode($r, true);
$chapters = [];
foreach ($d['data'] as $h) {
    if (isset($h['book_id']) && $h['book_id'] == 1) {
        $chapters[$h['chapter_id']] = ($chapters[$h['chapter_id']] ?? 0) + 1;
    }
}
if (empty($chapters)) { echo "No hadiths for book 1 in first 200 results\n"; } else {
    echo "Chapter distribution for book 1 (sample):\n"; print_r($chapters);
}
?>