<?php
$url = 'http://127.0.0.1:8000/api/chapters/2/hadiths';
$r = @file_get_contents($url);
if (!$r) { echo "NO RESPONSE\n"; exit(1);} 
$d = json_decode($r, true);
if (isset($d['data'][0])) { echo "OK: hadiths by chapter id\n"; echo json_encode($d['data'][0], JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT); } else { echo "NO hadiths by chapter id\n"; }
?>