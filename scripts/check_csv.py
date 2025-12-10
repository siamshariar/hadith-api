import csv
with open('csv_exports/categories_multilingual.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 5:
            break
        slug = row.get('slug', '').strip()
        print(f'Row {i}: slug="{slug}" len={len(slug)}')