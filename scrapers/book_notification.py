#!/usr/bin/env python3
"""
Book Notification scraper for centralized book release tracking.

Scrapes book release data from booknotification.com author pages.
"""

import re
from datetime import datetime, date
from typing import Dict, List, Optional
import logging
from .base_book_scraper import BaseBookScraper

logger = logging.getLogger(__name__)

class BookNotificationScraper(BaseBookScraper):
    """Scraper for Book Notification website."""
    
    def __init__(self):
        super().__init__("https://www.booknotification.com")
    
    def scrape_author_releases(self, author_config: Dict) -> List[Dict]:
        """
        Scrape book releases for a specific author from Book Notification.
        
        Args:
            author_config: Dictionary containing author configuration
            
        Returns:
            List of book dictionaries with release information
        """
        author_id = author_config.get('book_notification_id')
        author_name = author_config.get('name')
        
        if not author_id:
            logger.error(f"No book_notification_id provided for {author_name}")
            return []
        
        # Construct author URL
        author_url = f"{self.base_url}/authors/{author_id}"
        
        try:
            soup = self.scrape_page(author_url)
            if not soup:
                logger.error(f"Failed to scrape author page: {author_url}")
                return []
            
            # Look for FAQ sections with upcoming book information
            books = []
            
            # Look for FAQ patterns with upcoming book information
            self._extract_single_book_pattern(soup, books, author_name, author_url)
            self._extract_multiple_books_pattern(soup, books, author_name, author_url)
            
            # Filter for future releases only
            future_books = [book for book in books if self._is_future_date(book.get('release_date'))]
            
            return future_books
            
        except Exception as e:
            logger.error(f"Error scraping releases for {author_name}: {e}")
            return []
    
    def _extract_single_book_pattern(self, soup, books: List[Dict], author_name: str, author_url: str):
        """Extract single book pattern: 'Author has a new book coming out on DATE called TITLE'"""
        
        # Look for text containing the pattern "has a new book coming out"
        coming_out_texts = soup.find_all(string=lambda text: text and "has a new book coming out" in text)
        
        if coming_out_texts:
            for text in coming_out_texts:
                # The text is cut off, so get the parent element's full text
                if hasattr(text, 'parent') and text.parent:
                    parent_text = text.parent.get_text()
                    
                    # First try the complete pattern
                    pattern = r'(.+?)\s+has a new book coming out on\s+([^c]+?)called\s+(.+?)(?:\.|$)'
                    matches = re.search(pattern, parent_text, re.IGNORECASE)
                    
                    if matches:
                        extracted_author, date_str, title = matches.groups()
                        parsed_date = self.parse_release_date(date_str.strip())
                        
                        if parsed_date and title.strip():
                            book = self.normalize_book_data({
                                'title': title.strip(),
                                'author': author_name,
                                'release_date': parsed_date,
                                'source_url': author_url,
                                'metadata': {'source': 'faq', 'confidence': 'high'}
                            })
                            books.append(book)
                            logger.info(f"Found upcoming book: {title.strip()} - {parsed_date}")
                    else:
                        # Try a simpler pattern
                        simple_pattern = r'has a new book coming out on\s+(.+?)\s+called\s+(.+?)(?:\.|$)'
                        simple_matches = re.search(simple_pattern, parent_text, re.IGNORECASE)
                        if simple_matches:
                            date_str, title = simple_matches.groups()
                            parsed_date = self.parse_release_date(date_str.strip())
                            
                            if parsed_date and title.strip():
                                book = self.normalize_book_data({
                                    'title': title.strip(),
                                    'author': author_name,
                                    'release_date': parsed_date,
                                    'source_url': author_url,
                                    'metadata': {'source': 'faq', 'confidence': 'high'}
                                })
                                books.append(book)
                                logger.info(f"Found upcoming book: {title.strip()} - {parsed_date}")
    
    def _extract_multiple_books_pattern(self, soup, books: List[Dict], author_name: str, author_url: str):
        """Extract multiple books pattern: 'Author has X new books coming out: TITLE1 will be released on DATE1. TITLE2 will be released on DATE2.'"""
        
        # Look for text containing multiple books pattern
        multiple_books_texts = soup.find_all(string=lambda text: text and re.search(r'has.*books? coming out', text, re.IGNORECASE))
        
        if multiple_books_texts:
            for text in multiple_books_texts:
                if hasattr(text, 'parent') and text.parent:
                    parent_text = text.parent.get_text()
                    
                    # Pattern for individual book releases: "TITLE will be released on DATE"
                    book_pattern = r'([^.]+?)\s+will be released on\s+([^.]+?)(?:\.|$)'
                    book_matches = re.findall(book_pattern, parent_text, re.IGNORECASE)
                    
                    for title_match, date_match in book_matches:
                        title = title_match.strip()
                        date_str = date_match.strip()
                        
                        # Clean up the title - remove common prefix patterns
                        title = re.sub(r'^(and\s+)?', '', title, flags=re.IGNORECASE).strip()
                        title = re.sub(r'^.*?has.*?books?\s+coming\s+out:\s*', '', title, flags=re.IGNORECASE).strip()
                        title = re.sub(r'^.*?new\s+books?\s+coming\s+out:\s*', '', title, flags=re.IGNORECASE).strip()
                        
                        parsed_date = self.parse_release_date(date_str)
                        
                        if parsed_date and title and len(title) > 3:  # Basic validation
                            book = self.normalize_book_data({
                                'title': title,
                                'author': author_name,
                                'release_date': parsed_date,
                                'source_url': author_url,
                                'metadata': {'source': 'faq_multiple', 'confidence': 'high'}
                            })
                            books.append(book)
                            logger.info(f"Found upcoming book (multiple pattern): {title} - {parsed_date}")
    
    def parse_release_date(self, date_str: str) -> Optional[date]:
        """
        Parse release date from various date string formats.
        
        Args:
            date_str: Date string in various possible formats
            
        Returns:
            Parsed date object or None if parsing fails
        """
        if not date_str or not isinstance(date_str, str):
            return None
        
        # Clean the date string
        date_str = self.clean_text(date_str)
        
        # Common date patterns
        patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # 2025-12-09
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # 12/09/2025
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # 12-09-2025
            r'(\w{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})',  # December 9, 2025
            r'(\d{1,2})\s+(\w{3,9})\s+(\d{4})',  # 9 December 2025
            r'(\w{3,9})\s+(\d{4})',  # December 2025
            r'(\d{4})',  # 2025
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD format
                            year, month, day = groups
                            return date(int(year), int(month), int(day))
                        elif pattern.startswith(r'(\d{1,2})/'):  # MM/DD/YYYY format
                            month, day, year = groups
                            return date(int(year), int(month), int(day))
                        elif pattern.startswith(r'(\d{1,2})-'):  # MM-DD-YYYY format
                            month, day, year = groups
                            return date(int(year), int(month), int(day))
                        elif pattern.startswith(r'(\w{3,9})') and r'(\d{1,2})' in pattern:  # Month name formats
                            month_name, day, year = groups
                            month_num = self._parse_month_name(month_name)
                            if month_num:
                                return date(int(year), month_num, int(day))
                        elif pattern.startswith(r'(\d{1,2})\s+(\w{3,9})'):  # DD Month YYYY format
                            day, month_name, year = groups
                            month_num = self._parse_month_name(month_name)
                            if month_num:
                                return date(int(year), month_num, int(day))
                    elif len(groups) == 2:  # Month Year format
                        month_name, year = groups
                        month_num = self._parse_month_name(month_name)
                        if month_num:
                            return date(int(year), month_num, 1)  # Default to 1st of month
                    elif len(groups) == 1:  # Year only
                        year = groups[0]
                        return date(int(year), 1, 1)  # Default to January 1st
                        
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _parse_month_name(self, month_name: str) -> Optional[int]:
        """Parse month name to month number."""
        if not month_name:
            return None
            
        month_name = month_name.lower()
        
        months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        return months.get(month_name)
    
    def _is_future_date(self, date_obj) -> bool:
        """Check if date is in the future."""
        try:
            if isinstance(date_obj, str):
                date_obj = self.parse_release_date(date_obj)
            
            if isinstance(date_obj, date):
                return date_obj >= date.today()
            
            return False
        except:
            return False