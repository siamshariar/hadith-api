
from utils import get_db_connection


def main():
    conn = get_db_connection()
    cur = conn.cursor()

    checks = [
        ('Languages', 'SELECT COUNT(*) FROM languages'),
        ('Categories', 'SELECT COUNT(*) FROM categories'),
        ('Category translations', 'SELECT COUNT(*) FROM category_translations'),
        ('Chapters', 'SELECT COUNT(*) FROM chapters'),
        ('Hadiths', 'SELECT COUNT(*) FROM hadiths'),
        ('Hadith translations', 'SELECT COUNT(*) FROM hadith_translations')
    ]

    for name, sql in checks:
        cur.execute(sql)
        print(f"{name}: {cur.fetchone()[0]}")

    # Translation coverage by language
    print('\nTranslation coverage by language:')
    cur.execute('SELECT localization_code, COUNT(*) FROM hadith_translations GROUP BY localization_code ORDER BY COUNT(*) DESC')
    for row in cur.fetchall():
        print(f"  {row[0]} : {row[1]}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
