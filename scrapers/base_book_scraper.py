#!/usr/bin/env python3
"""
Base scraper interface for multi-source book release monitoring.

Defines the common interface and utilities that all book scrapers should implement.
"""

import requests
import json
import re
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class BaseBookScraper(ABC):
    """Abstract base class for all book release scrapers."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Set common headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    @abstractmethod
    def scrape_author_releases(self, author_config: Dict) -> List[Dict]:
        """
        Scrape book releases for a specific author.
        
        Args:
            author_config: Dictionary containing author configuration from authors.yaml
            
        Returns:
            List of book dictionaries with release information
        """
        pass
    
    @abstractmethod
    def parse_release_date(self, date_str: str) -> Optional[date]:
        """
        Parse release date from various date string formats.
        
        Args:
            date_str: Date string in various possible formats
            
        Returns:
            Parsed date object or None if parsing fails
        """
        pass
    
    def extract_json_ld(self, soup: BeautifulSoup, schema_type: str = "Book") -> Optional[Dict]:
        """
        Extract JSON-LD structured data from script tags.
        
        Args:
            soup: BeautifulSoup object
            schema_type: The @type to look for (e.g., "Book", "Product")
            
        Returns:
            Dict containing the structured data, or None if not found
        """
        try:
            # Find all JSON-LD script tags
            json_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_scripts:
                if not script.string:
                    continue
                    
                try:
                    data = json.loads(script.string)
                    
                    # Handle single objects
                    if isinstance(data, dict):
                        if data.get('@type') == schema_type:
                            return data
                        # Handle nested structures
                        if '@graph' in data:
                            for item in data['@graph']:
                                if isinstance(item, dict) and item.get('@type') == schema_type:
                                    return item
                    
                    # Handle arrays of objects
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == schema_type:
                                return item
                                
                except json.JSONDecodeError:
                    continue
                    
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting JSON-LD: {e}")
            return None
    
    def generate_book_id(self, title: str, author: str) -> str:
        """
        Generate the identifier for a book: the full author name and title, normalised.

        The release date is deliberately not part of it, so a date change keeps the same ID.
        """
        words = re.sub(r'[^\w\s]', '', f"{author} {title}".lower()).split()
        return '_'.join(words)

    def normalize_book_data(self, raw_data: Dict) -> Dict:
        """
        Normalize book data into standard format.
        
        Args:
            raw_data: Raw book data from scraper
            
        Returns:
            Normalized book data dictionary
        """
        title = raw_data.get('title', '').strip()
        author = raw_data.get('author', '').strip()

        return {
            'id': self.generate_book_id(title, author),
            'title': title,
            'author': author,
            'release_date': raw_data.get('release_date'),
            'status': raw_data.get('status', 'upcoming'),
            'source_url': raw_data.get('source_url', ''),
            'discovery_date': datetime.now().isoformat(),
            'last_checked': datetime.now().isoformat(),
            'notifications_sent': [],
            'metadata': raw_data.get('metadata', {})
        }

    def scrape_page(self, url: str, timeout: int = 30) -> BeautifulSoup:
        """
        Scrape a web page and return BeautifulSoup object.

        Args:
            url: URL to scrape
            timeout: Request timeout in seconds

        Raises:
            requests.RequestException: if the page cannot be fetched
        """
        logger.info(f"Scraping page: {url}")

        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()

        return BeautifulSoup(response.content, 'html.parser')
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        text = text.strip()
        
        return text