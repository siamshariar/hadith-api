<?php

$url = 'http://127.0.0.1:8000/api/categories/3?language=bn&include_hadiths=true&limit=1';
$response = file_get_contents($url);
$data = json_decode($response, true);

if ($data && isset($data['data']['subcategories'][0]['hadiths'][0]['translation']['translation_text'])) {
    $text = $data['data']['subcategories'][0]['hadiths'][0]['translation']['translation_text'];
    
    // Show last 400 characters to see the reference part
    echo "=== Bengali Translation (last 400 chars) ===\n";
    echo mb_substr($text, -400, null, 'UTF-8') . "\n";
    
    // Check if it contains the garbled text
    if (strpos($text, 'খণ্ড') !== false) {
        echo "\n❌ PROBLEM: Still contains garbled text (খণ্ড pattern found)\n";
    } else {
        echo "\n✅ GOOD: No garbled text detected\n";
    }
    
    // Check if it contains proper Bengali references
    if (preg_match('/\(বুখারীঃ\s*৪৪৯৭/', $text)) {
        echo "✅ GOOD: Contains proper Bengali reference (বুখারীঃ ৪৪৯৭)\n";
    }
}
