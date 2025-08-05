#!/usr/bin/env python3
"""
Local testing script for book scraper development.
"""

import os
import sys
from scrapers import BookNotificationScraper

def test_author_scraping(author_name, author_id):
    """Test scraping for a specific author."""
    
    print(f"\n=== Testing {author_name} ===")
    print(f"Author ID: {author_id}")
    print(f"URL: https://www.booknotification.com/authors/{author_id}")
    
    scraper = BookNotificationScraper()
    
    author_config = {
        'name': author_name,
        'book_notification_id': author_id
    }
    
    try:
        books = scraper.scrape_author_releases(author_config)
        print(f"Found {len(books)} books")
        
        for i, book in enumerate(books, 1):
            print(f"\nBook {i}:")
            print(f"  Title: {book.get('title', 'N/A')}")
            print(f"  Release Date: {book.get('release_date', 'N/A')}")
            print(f"  Source: {book.get('source_url', 'N/A')}")
            if book.get('metadata'):
                print(f"  Metadata: {book['metadata']}")
                
    except Exception as e:
        print(f"Error testing {author_name}: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Test scraper with different authors."""
    
    print("Book Release Scraper - Local Testing")
    print("====================================")
    
    # Test authors (start with the problematic one)
    test_authors = [
        ("James S. A. Corey", "james-s-a-corey"),
        ("Brandon Sanderson", "brandon-sanderson"),
    ]
    
    for author_name, author_id in test_authors:
        test_author_scraping(author_name, author_id)
    
    print("\n=== Testing Complete ===")

if __name__ == "__main__":
    main()