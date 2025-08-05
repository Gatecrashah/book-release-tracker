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
            
            books = []
            
            # Try to extract JSON-LD data first
            json_ld_books = self._extract_books_from_json_ld(soup, author_name)
            books.extend(json_ld_books)
            
            # Supplement with HTML parsing for upcoming releases
            html_books = self._extract_books_from_html(soup, author_name, author_url)
            books.extend(html_books)
            
            # Remove duplicates based on book ID
            unique_books = self._deduplicate_books(books)
            
            # Filter for upcoming releases only
            upcoming_books = [book for book in unique_books if self._is_upcoming_release(book)]
            
            logger.info(f"Found {len(upcoming_books)} upcoming releases for {author_name}")
            return upcoming_books
            
        except Exception as e:
            logger.error(f"Error scraping releases for {author_name}: {e}")
            return []
    
    def _extract_books_from_json_ld(self, soup, author_name: str) -> List[Dict]:
        """Extract book data from JSON-LD structured data."""
        books = []
        
        try:
            # Look for various JSON-LD schema types
            for schema_type in ['Book', 'Product', 'WebPage']:
                json_data = self.extract_json_ld(soup, schema_type)
                if json_data:
                    book = self._parse_json_ld_book(json_data, author_name)
                    if book:
                        books.append(book)
                        
            # Also check for @graph structures with multiple books
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                if script.string and '@graph' in script.string:
                    import json
                    try:
                        data = json.loads(script.string)
                        if '@graph' in data:
                            for item in data['@graph']:
                                if item.get('@type') in ['Book', 'Product']:
                                    book = self._parse_json_ld_book(item, author_name)
                                    if book:
                                        books.append(book)
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.debug(f"Error extracting JSON-LD books: {e}")
            
        return books
    
    def _extract_books_from_html(self, soup, author_name: str, source_url: str) -> List[Dict]:
        """Extract book data from HTML elements."""
        books = []
        
        try:
            # Look for upcoming releases section
            upcoming_section = soup.find('section', class_=re.compile(r'upcoming|releases|books'))
            if not upcoming_section:
                # Try alternative selectors
                upcoming_section = soup.find('div', {'id': re.compile(r'upcoming|releases')})
            
            if upcoming_section:
                # Look for book entries in various formats
                book_elements = upcoming_section.find_all(['div', 'li', 'tr'], 
                                                        class_=re.compile(r'book|release|item'))
                
                for element in book_elements:
                    book = self._parse_html_book_element(element, author_name, source_url)
                    if book:
                        books.append(book)
            
            # Also look for table-based book listings
            tables = soup.find_all('table')
            for table in tables:
                if self._is_book_table(table):
                    table_books = self._parse_book_table(table, author_name, source_url)
                    books.extend(table_books)
                    
        except Exception as e:
            logger.debug(f"Error extracting HTML books: {e}")
            
        return books
    
    def _parse_json_ld_book(self, json_data: Dict, author_name: str) -> Optional[Dict]:
        """Parse a book from JSON-LD data."""
        try:
            title = json_data.get('name') or json_data.get('title', '')
            if not title:
                return None
            
            # Extract publication date
            pub_date = None
            for date_field in ['datePublished', 'releaseDate', 'publicationDate']:
                if date_field in json_data:
                    pub_date = self.parse_release_date(json_data[date_field])
                    break
            
            # Extract additional metadata
            metadata = {
                'isbn': json_data.get('isbn', ''),
                'publisher': json_data.get('publisher', {}).get('name', '') if isinstance(json_data.get('publisher'), dict) else json_data.get('publisher', ''),
                'series': json_data.get('isPartOf', {}).get('name', '') if isinstance(json_data.get('isPartOf'), dict) else '',
                'description': json_data.get('description', ''),
                'url': json_data.get('url', '')
            }
            
            return self.normalize_book_data({
                'title': self.clean_text(title),
                'author': author_name,
                'release_date': pub_date,
                'source_url': json_data.get('url', ''),
                'metadata': metadata
            })
            
        except Exception as e:
            logger.debug(f"Error parsing JSON-LD book: {e}")
            return None
    
    def _parse_html_book_element(self, element, author_name: str, source_url: str) -> Optional[Dict]:
        """Parse a book from HTML element."""
        try:
            # Try to find title
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|book'))
            if not title_elem:
                title_elem = element.find('a')  # Fallback to any link
            
            if not title_elem:
                return None
                
            title = self.clean_text(title_elem.get_text())
            if not title:
                return None
            
            # Try to find release date
            release_date = None
            date_elem = element.find(['span', 'div', 'time'], class_=re.compile(r'date|release|publish'))
            if date_elem:
                date_text = self.clean_text(date_elem.get_text())
                release_date = self.parse_release_date(date_text)
            
            # Look for series information
            series_elem = element.find(['span', 'div'], class_=re.compile(r'series'))
            series = self.clean_text(series_elem.get_text()) if series_elem else ''
            
            metadata = {
                'series': series,
                'html_source': True
            }
            
            return self.normalize_book_data({
                'title': title,
                'author': author_name,
                'release_date': release_date,
                'source_url': source_url,
                'metadata': metadata
            })
            
        except Exception as e:
            logger.debug(f"Error parsing HTML book element: {e}")
            return None
    
    def _parse_book_table(self, table, author_name: str, source_url: str) -> List[Dict]:
        """Parse books from HTML table."""
        books = []
        
        try:
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                # Assume first cell is title, look for date in other cells
                title = self.clean_text(cells[0].get_text())
                if not title:
                    continue
                
                release_date = None
                for cell in cells[1:]:
                    date_text = self.clean_text(cell.get_text())
                    parsed_date = self.parse_release_date(date_text)
                    if parsed_date:
                        release_date = parsed_date
                        break
                
                book = self.normalize_book_data({
                    'title': title,
                    'author': author_name,
                    'release_date': release_date,
                    'source_url': source_url,
                    'metadata': {'table_source': True}
                })
                
                books.append(book)
                
        except Exception as e:
            logger.debug(f"Error parsing book table: {e}")
            
        return books
    
    def _is_book_table(self, table) -> bool:
        """Check if table contains book data."""
        try:
            # Look for typical book table headers
            headers = table.find_all(['th', 'td'])[:5]  # Check first few cells
            header_text = ' '.join([cell.get_text().lower() for cell in headers])
            
            book_keywords = ['title', 'book', 'release', 'date', 'publish', 'series']
            return any(keyword in header_text for keyword in book_keywords)
            
        except Exception:
            return False
    
    def _deduplicate_books(self, books: List[Dict]) -> List[Dict]:
        """Remove duplicate books based on title and author."""
        seen = set()
        unique_books = []
        
        for book in books:
            key = (book['title'].lower(), book['author'].lower())
            if key not in seen:
                seen.add(key)
                unique_books.append(book)
                
        return unique_books
    
    def _is_upcoming_release(self, book: Dict) -> bool:
        """Check if book is an upcoming release."""
        release_date = book.get('release_date')
        if not release_date:
            return True  # Include books without dates as potentially upcoming
        
        if isinstance(release_date, str):
            release_date = self.parse_release_date(release_date)
        
        if isinstance(release_date, date):
            return release_date >= date.today()
            
        return True  # Include if we can't determine the date
    
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
            r'(\w{3,9})\s+(\d{1,2}),?\s+(\d{4})',  # December 9, 2025
            r'(\d{1,2})\s+(\w{3,9})\s+(\d{4})',  # 9 December 2025
            r'(\w{3,9})\s+(\d{4})',  # December 2025
            r'(\d{4})',  # 2025
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 3:
                        if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD format
                            year, month, day = match.groups()
                            return date(int(year), int(month), int(day))
                        elif pattern.startswith(r'(\d{1,2})/'):  # MM/DD/YYYY format
                            month, day, year = match.groups()
                            return date(int(year), int(month), int(day))
                        elif pattern.startswith(r'(\d{1,2})-'):  # MM-DD-YYYY format
                            month, day, year = match.groups()
                            return date(int(year), int(month), int(day))
                        elif pattern.startswith(r'(\w{3,9})') and r'(\d{1,2})' in pattern:  # Month name formats
                            month_name, day, year = match.groups()
                            month_num = self._parse_month_name(month_name)
                            if month_num:
                                return date(int(year), month_num, int(day))
                        elif pattern.startswith(r'(\d{1,2})\s+(\w{3,9})'):  # DD Month YYYY format
                            day, month_name, year = match.groups()
                            month_num = self._parse_month_name(month_name)
                            if month_num:
                                return date(int(year), month_num, int(day))
                    elif len(match.groups()) == 2:  # Month Year format
                        month_name, year = match.groups()
                        month_num = self._parse_month_name(month_name)
                        if month_num:
                            return date(int(year), month_num, 1)  # Default to 1st of month
                    elif len(match.groups()) == 1:  # Year only
                        year = match.groups()[0]
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