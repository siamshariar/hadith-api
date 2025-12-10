<?php
$url = 'http://127.0.0.1:8000/api/books?include_hadiths=true&language=en&limit=2';
$r = @file_get_contents($url);
if (!$r) {
    echo "FAIL: no response\n";
    exit(1);
}
$d = json_decode($r, true);
if (isset($d['data'][0])) {
    echo "OK: got books\n";
    echo "Sample first book:\n";
    echo json_encode($d['data'][0], JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT);
} else {
    echo "FAIL: no data\n";
}
?>