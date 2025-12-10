<?php
$pdo = new PDO('sqlite:database/database.sqlite');

echo "=== HADITH DATABASE CHECK ===\n\n";

// Get total count
$stmt = $pdo->query('SELECT COUNT(*) as total FROM hadiths');
$count = $stmt->fetch()['total'];
echo "Total hadiths: $count\n\n";

// Get first 10 hadiths
echo "First 10 hadiths:\n";
$stmt = $pdo->query('SELECT id, hadith_number, book_id FROM hadiths ORDER BY id LIMIT 10');
while($row = $stmt->fetch()) {
    echo "ID: {$row['id']}, Number: {$row['hadith_number']}, Book: {$row['book_id']}\n";
}

echo "\n=== CHECKING FOR ID 1 ===\n";
$stmt = $pdo->prepare('SELECT id, hadith_number, book_id FROM hadiths WHERE id = ?');
$stmt->execute([1]);
$hadith = $stmt->fetch();
if ($hadith) {
    echo "Hadith ID 1 exists: " . json_encode($hadith) . "\n";
} else {
    echo "Hadith ID 1 does NOT exist!\n";
}

echo "\n=== CHECKING TRANSLATIONS FOR ID 1 ===\n";
$stmt = $pdo->prepare('SELECT COUNT(*) as count FROM hadith_translations WHERE hadith_id = ?');
$stmt->execute([1]);
$translationCount = $stmt->fetch()['count'];
echo "Translations for hadith ID 1: $translationCount\n";

if ($translationCount > 0) {
    $stmt = $pdo->prepare('SELECT language_code, translation_text FROM hadith_translations WHERE hadith_id = ? LIMIT 3');
    $stmt->execute([1]);
    while($row = $stmt->fetch()) {
        echo "Language: {$row['language_code']}, Text: " . substr($row['translation_text'], 0, 50) . "...\n";
    }
}
?>