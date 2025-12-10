<?php

require 'vendor/autoload.php';
$app = require_once 'bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

$hadith = App\Models\Hadith::find(75963);

$bnTrans = $hadith->translations()->where('localization_code', 'bn')->first();
$enTrans = $hadith->translations()->where('localization_code', 'en')->first();
$ruTrans = $hadith->translations()->where('localization_code', 'ru')->first();

echo "=== BENGALI TRANSLATION (last 300 chars) ===\n";
echo substr($bnTrans->translation_text, -300) . "\n\n";

echo "=== ENGLISH TRANSLATION (last 300 chars) ===\n";
echo substr($enTrans->translation_text, -300) . "\n\n";

echo "=== RUSSIAN TRANSLATION (last 300 chars) ===\n";
echo substr($ruTrans->translation_text, -300) . "\n\n";

// Check reference translations
echo "\n=== REFERENCE TRANSLATIONS ===\n";
$bnRef = $hadith->referenceTranslations()->where('localization_code', 'bn')->first();
$enRef = $hadith->referenceTranslations()->where('localization_code', 'en')->first();
$ruRef = $hadith->referenceTranslations()->where('localization_code', 'ru')->first();

echo "Bengali ref exists: " . ($bnRef ? "YES" : "NO") . "\n";
echo "English ref exists: " . ($enRef ? "YES" : "NO") . "\n";
echo "Russian ref exists: " . ($ruRef ? "YES" : "NO") . "\n";

if ($bnRef) {
    echo "\nBengali ref (first 200 chars):\n";
    echo substr($bnRef->references_text, 0, 200) . "\n";
}

if ($enRef) {
    echo "\nEnglish ref (first 200 chars):\n";
    echo substr($enRef->references_text, 0, 200) . "\n";
}
