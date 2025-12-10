<?php

echo "=== Check English Number Localization ===\n\n";
$en = file_get_contents('http://127.0.0.1:8000/api/categories/3?language=en&include_hadiths=true&limit=1');
$enData = json_decode($en, true);
$enText = $enData['data']['subcategories'][0]['hadiths'][0]['translation']['translation_text'];

echo "Full translation text:\n";
echo $enText . "\n\n";

// Look for the main reference numbers
if (preg_match('/البخاري.*?\((\d+)\/\s*(\d+)\).*?\((\d+)\)/', $enText, $matches)) {
    echo "Found Bukhari reference:\n";
    echo "  - Volume/Page: {$matches[1]}/{$matches[2]}\n";
    echo "  - Hadith number: {$matches[3]}\n";
    
    if ($matches[3] === '4497') {
        echo "  ✅ Number 4497 is in Western numerals (correct for English)\n";
    } else {
        echo "  ❌ Number is: {$matches[3]}\n";
    }
}

if (preg_match('/مسلم.*?\((\d+)\/\s*(\d+)\).*?\((\d+)\)/', $enText, $matches)) {
    echo "\nFound Muslim reference:\n";
    echo "  - Volume/Page: {$matches[1]}/{$matches[2]}\n";
    echo "  - Hadith number: {$matches[3]}\n";
    
    if ($matches[3] === '92') {
        echo "  ✅ Number 92 is in Western numerals (correct for English)\n";
    } else {
        echo "  ❌ Number is: {$matches[3]}\n";
    }
}
