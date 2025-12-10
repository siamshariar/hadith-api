<?php
$url = 'http://127.0.0.1:8000/api/books/1/chapters/1/hadeeths?language=en&page=1';
$r = @file_get_contents($url);
if (!$r) { echo "FAIL: no response\n"; exit(1);} $d = json_decode($r, true);
if (isset($d['data'][0])) { echo "OK: got hadiths for chapter 1\n"; echo json_encode($d['data'][0], JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT); } else { echo "FAIL: no hadiths for chapter 1\n"; }
?>