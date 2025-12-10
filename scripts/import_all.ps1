# Import all HadeethEnc categories
Write-Host "Importing Category 1..." -ForegroundColor Yellow
python scripts\step5_import_one_category.py 1

Write-Host "Importing Category 2..." -ForegroundColor Yellow  
python scripts\step5_import_one_category.py 2

Write-Host "Importing Category 3..." -ForegroundColor Yellow
python scripts\step5_import_one_category.py 3

Write-Host "Importing Category 4..." -ForegroundColor Yellow
python scripts\step5_import_one_category.py 4

Write-Host "Importing Category 5..." -ForegroundColor Yellow
python scripts\step5_import_one_category.py 5

Write-Host "Importing Category 6..." -ForegroundColor Yellow
python scripts\step5_import_one_category.py 6

Write-Host "Importing Category 7..." -ForegroundColor Yellow
python scripts\step5_import_one_category.py 7

Write-Host ""
Write-Host "ALL CATEGORIES IMPORTED!" -ForegroundColor Green
Write-Host "Run: python scripts\check_all_books.py" -ForegroundColor Cyan
