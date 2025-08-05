#!/usr/bin/env python3
"""
Book scraper modules for multi-source book release monitoring.
"""

from .base_book_scraper import BaseBookScraper
from .book_notification import BookNotificationScraper

__all__ = ['BaseBookScraper', 'BookNotificationScraper']