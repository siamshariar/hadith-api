#!/usr/bin/env python3
"""
Test script to verify Hadith API is working
"""

import requests
import json

def test_api():
    base_url = "http://127.0.0.1:8000/api"

    print("Testing Hadith API endpoints...")

    # Test books endpoint
    try:
        response = requests.get(f"{base_url}/books", timeout=5)
        if response.status_code == 200:
            books = response.json()
            print(f"✅ Books endpoint: {len(books)} books found")
            if books:
                print(f"   First book: {books[0].get('name_en', 'Unknown')}")
        else:
            print(f"❌ Books endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Books endpoint error: {e}")

    # Test specific book
    try:
        response = requests.get(f"{base_url}/books/bukhari", timeout=5)
        if response.status_code == 200:
            book = response.json()
            print(f"✅ Bukhari book: {book.get('name_en', 'Unknown')}")
            print(f"   Total hadith: {book.get('total_hadith', 0)}")
        else:
            print(f"❌ Bukhari book failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Bukhari book error: {e}")

    # Test chapters
    try:
        response = requests.get(f"{base_url}/books/bukhari/chapters", timeout=5)
        if response.status_code == 200:
            chapters = response.json()
            print(f"✅ Bukhari chapters: {len(chapters)} chapters found")
            if chapters:
                print(f"   First chapter: {chapters[0].get('name_en', 'Unknown')}")
        else:
            print(f"❌ Chapters failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Chapters error: {e}")

    # Test hadiths
    try:
        response = requests.get(f"{base_url}/books/bukhari/chapters/1", timeout=5)
        if response.status_code == 200:
            hadiths = response.json()
            print(f"✅ Chapter 1 hadiths: {len(hadiths)} hadiths found")
            if hadiths:
                hadith = hadiths[0]
                print(f"   First hadith: #{hadith.get('hadith_number', 'Unknown')}")
                print(f"   Has Arabic: {'Yes' if hadith.get('arabic_text') else 'No'}")
                print(f"   Translations: {len(hadith.get('translations', []))}")
        else:
            print(f"❌ Hadiths failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Hadiths error: {e}")

    print("\nAPI test completed!")

if __name__ == "__main__":
    test_api()