<?php

echo "=== Testing English API ===\n";
$url = 'http://127.0.0.1:8000/api/categories/3?language=en&include_hadiths=true&limit=1';
$response = file_get_contents($url);
$data = json_decode($response, true);

if ($data && isset($data['data']['subcategories'][0]['hadiths'][0]['translation']['translation_text'])) {
    $text = $data['data']['subcategories'][0]['hadiths'][0]['translation']['translation_text'];
    
    // Show last 600 characters to see the reference part
    echo "\nEnglish Translation (last 600 chars):\n";
    echo substr($text, -600) . "\n";
    
    // Check if it contains references
    if (preg_match('/Sahih|Bukhari|Muslim|\(\d+\)/', $text)) {
        echo "\n✅ GOOD: Contains references\n";
    } else {
        echo "\n❌ PROBLEM: No references found\n";
    }
    
    // Check for proper numbers
    if (preg_match('/4497|92/', $text)) {
        echo "✅ GOOD: Contains hadith numbers (4497, 92)\n";
    }
}

echo "\n\n=== Testing Russian API ===\n";
$url = 'http://127.0.0.1:8000/api/categories/3?language=ru&include_hadiths=true&limit=1';
$response = file_get_contents($url);
$data = json_decode($response, true);

if ($data && isset($data['data']['subcategories'][0]['hadiths'][0]['translation']['translation_text'])) {
    $text = $data['data']['subcategories'][0]['hadiths'][0]['translation']['translation_text'];
    
    // Show last 400 characters
    echo "\nRussian Translation (last 400 chars):\n";
    echo mb_substr($text, -400, null, 'UTF-8') . "\n";
    
    // Check if it contains references
    if (preg_match('/Бухари|Муслим|صحيح/', $text)) {
        echo "\n✅ GOOD: Contains references\n";
    } else {
        echo "\n❌ PROBLEM: No references found\n";
    }
}
