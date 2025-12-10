<?php

require 'vendor/autoload.php';
$app = require_once 'bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

$hadith = App\Models\Hadith::find(75963);
$enRef = $hadith->referenceTranslations()->where('localization_code', 'en')->first();

if ($enRef) {
    $decoded1 = json_decode($enRef->references_text, true);
    echo "=== First Level Decode ===\n";
    echo "Type: " . gettype($decoded1) . "\n";
    echo "Count: " . count($decoded1) . "\n";
    echo "First element type: " . gettype($decoded1[0]) . "\n";
    echo "First 200 chars of first element:\n";
    echo substr($decoded1[0], 0, 200) . "\n\n";
    
    if (is_string($decoded1[0])) {
        $decoded2 = json_decode($decoded1[0], true);
        echo "=== Second Level Decode ===\n";
        echo "Type: " . gettype($decoded2) . "\n";
        echo "Count: " . count($decoded2) . "\n";
        echo "\nFirst 50 elements:\n";
        print_r(array_slice($decoded2, 0, 50));
        
        echo "\n\n=== What it looks like joined ===\n";
        echo implode('', $decoded2) . "\n";
    }
}
