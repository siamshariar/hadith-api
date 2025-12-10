<?php
$config = require 'config/database.php';
$conn = new mysqli('127.0.0.1', 'root', '123456', 'hadith_api_prod');

echo 'Hadiths: ' . $conn->query('SELECT COUNT(*) FROM hadiths')->fetch_row()[0] . PHP_EOL;
echo 'Translations: ' . $conn->query('SELECT COUNT(*) FROM hadith_translations')->fetch_row()[0] . PHP_EOL;
echo 'Books: ' . $conn->query('SELECT COUNT(*) FROM books')->fetch_row()[0] . PHP_EOL;
echo 'Chapters: ' . $conn->query('SELECT COUNT(*) FROM chapters')->fetch_row()[0] . PHP_EOL;

$conn->close();
?>