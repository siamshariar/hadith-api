<?php
$url = 'http://127.0.0.1:8000/api/books?include_hadiths=true&language=en&limit=2';
$r = @file_get_contents($url);
if (!$r) { echo "Fail: no response\n"; exit(1);} 
$d = json_decode($r, true);
if (isset($d['data'][0]['chapters'][0]['hadiths'][0])) echo "OK: chapter0 had hadiths\n"; else echo "NO hadiths in chapter0\n";
if (isset($d['data'][0]['chapters'][1]['hadiths'][0])) echo "OK: chapter1 had hadiths\n"; else echo "NO hadiths in chapter1\n";

// Print sample info for first two chapters
echo "Sample chapter counts: \n";
foreach ($d['data'][0]['chapters'] as $i => $c) {
    echo "Chapter {$i} => hadiths: " . count($c['hadiths']) . "\n";
}
?>