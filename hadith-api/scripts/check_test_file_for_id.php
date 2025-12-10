<?php
$id = (int)$argv[1];
$path = __DIR__ . '/../test_bengali_output.json';
if (!file_exists($path)) {
    echo "Test file not found: $path\n";
    exit(1);
}
$contents = file_get_contents($path);
if (strpos($contents, '"id":' . $id) !== false) {
    echo "Found $id in test file\n";
} else {
    echo "Not found $id in test file\n";
}
?>