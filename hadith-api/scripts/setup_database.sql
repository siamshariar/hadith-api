-- Create database
CREATE DATABASE IF NOT EXISTS hadith_api_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hadith_api_prod;

-- Enable foreign key checks
SET FOREIGN_KEY_CHECKS = 0;

-- Run all your migration files in order
-- 2024_01_01_000001_create_books_table.php
-- 2024_01_01_000002_create_books_localizations_table.php
-- 2024_01_01_000003_create_chapters_table.php
-- etc...

-- Create additional tables for enhanced data
CREATE TABLE IF NOT EXISTS hadith_details (
    id INT PRIMARY KEY AUTO_INCREMENT,
    hadith_id INT NOT NULL,
    explanation_ar TEXT,
    explanation_en TEXT,
    hints_ar JSON,
    hints_en JSON,
    references_ar JSON,
    references_en JSON,
    word_meanings_ar TEXT,
    word_meanings_en TEXT,
    narrator_ar VARCHAR(500),
    narrator_en VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (hadith_id) REFERENCES hadiths(id) ON DELETE CASCADE,
    INDEX idx_hadith_id (hadith_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create table for translation sources
CREATE TABLE IF NOT EXISTS translation_sources (
    id INT PRIMARY KEY AUTO_INCREMENT,
    source_name VARCHAR(100) NOT NULL,
    source_url VARCHAR(500),
    language_code VARCHAR(10),
    book_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source_language (source_name, language_code),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert known translation sources
INSERT INTO translation_sources (source_name, source_url, language_code) VALUES
('fawazahmed0', 'https://github.com/fawazahmed0/hadith-api', 'multi'),
('hadeethenc', 'https://hadeethenc.com/api/v1', 'multi'),
('alquranbd', 'https://alquranbd.com', 'bn');

-- Create statistics table
CREATE TABLE IF NOT EXISTS import_statistics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    import_date DATE NOT NULL,
    source_name VARCHAR(100),
    books_imported INT DEFAULT 0,
    chapters_imported INT DEFAULT 0,
    hadiths_imported INT DEFAULT 0,
    translations_imported INT DEFAULT 0,
    details_imported INT DEFAULT 0,
    duration_seconds INT,
    status VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_import_date (import_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- Create views for easy querying
CREATE OR REPLACE VIEW vw_hadith_complete AS
SELECT 
    h.id,
    h.hadith_number,
    h.arabic_text,
    h.grade,
    hd.explanation_ar,
    hd.explanation_en,
    hd.hints_ar,
    hd.hints_en,
    hd.references_ar,
    hd.references_en,
    hd.word_meanings_ar,
    hd.word_meanings_en,
    hd.narrator_ar,
    hd.narrator_en,
    b.code as book_code,
    b.name_en as book_name_en,
    b.name_ar as book_name_ar,
    c.chapter_no,
    c.name_en as chapter_name_en,
    c.name_ar as chapter_name_ar,
    GROUP_CONCAT(DISTINCT ht.localization_code) as available_languages
FROM hadiths h
LEFT JOIN hadith_details hd ON hd.hadith_id = h.id
LEFT JOIN books b ON b.id = h.book_id
LEFT JOIN chapters c ON c.id = h.chapter_id
LEFT JOIN hadith_translations ht ON ht.hadith_id = h.id
GROUP BY h.id;

-- Create view for category statistics
CREATE OR REPLACE VIEW vw_category_stats AS
SELECT 
    c.id,
    c.name_en,
    c.name_ar,
    COUNT(DISTINCT hc.hadith_id) as hadith_count,
    COUNT(DISTINCT sc.id) as subcategory_count
FROM categories c
LEFT JOIN hadith_category hc ON hc.category_id = c.id
LEFT JOIN categories sc ON sc.parent_id = c.id
GROUP BY c.id;