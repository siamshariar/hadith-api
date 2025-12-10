<?php

require 'vendor/autoload.php';
$app = require_once 'bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

// Check what Arabic references look like
$hadith = App\Models\Hadith::find(75963);
$arRef = $hadith->referenceTranslations()->where('localization_code', 'ar')->first();

if ($arRef) {
    echo "=== Arabic Reference ===\n";
    $decoded = json_decode($arRef->references_text, true);
    print_r($decoded);
    
    echo "\n\n=== Joined ===\n";
    if (is_array($decoded)) {
        echo implode("\n", $decoded) . "\n";
    }
}
