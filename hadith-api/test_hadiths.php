<?php
$url = 'http://127.0.0.1:8000/api/hadiths?per_page=50&page=1';
$r = @file_get_contents($url);
if (!$r) { echo "NO RESPONSE\n"; exit(1);} 
$d = json_decode($r, true);
if (!$d) { echo "Invalid JSON\n"; exit(1); }
echo "Got " . count($d['data']) . " hadiths\n";
$sample = array_slice($d['data'], 0, 5);
echo json_encode($sample, JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT);
?>