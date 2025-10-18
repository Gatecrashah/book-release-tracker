#!/usr/bin/env python3
"""
Main orchestration module for book release monitoring.

Coordinates scraping, data management, and email notifications.
"""

import json
import yaml
import logging
import copy
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import os
import sys

from scrapers import BookNotificationScraper
from email_sender import EmailSender

logger = logging.getLogger(__name__)

class BookMonitor:
    """Main book release monitoring coordinator."""
    
    def __init__(self):
        self.scraper = BookNotificationScraper()
        self.email_sender = EmailSender()
        self.authors_file = "authors.yaml"
        self.schedules_file = "release_schedules.json"
        
    def run_monitoring_cycle(self):
        """Run complete monitoring cycle: scrape, detect changes, send notifications."""
        
        logger.info("Starting book release monitoring cycle")
        
        try:
            # Load configuration
            authors = self.load_authors()
            if not authors:
                logger.error("No authors found in configuration")
                return False
            
            # Load existing release schedules
            existing_schedules = self.load_release_schedules()
            
            # Scrape all authors for new releases
            all_discovered_books = []
            for author in authors:
                if author.get('status') != 'active':
                    continue

                logger.info(f"Scraping releases for {author['name']}")
                books = self.scraper.scrape_author_releases(author)
                all_discovered_books.extend(books)

            # Process discovered books (only if any were found)
            new_discoveries = []
            date_changes = []

            if all_discovered_books:
                for book in all_discovered_books:
                    existing_book = self.find_existing_book(book, existing_schedules)

                    if not existing_book:
                        # New book discovery
                        new_discoveries.append(book)
                        logger.info(f"New book discovered: {book['title']} by {book['author']}")
                    else:
                        # Check for date changes
                        if self.has_date_changed(book, existing_book):
                            date_changes.append({
                                'book': book,
                                'old_date': existing_book.get('release_date'),
                                'new_date': book.get('release_date')
                            })
                            logger.info(f"Release date changed for: {book['title']}")
            else:
                logger.info("No books discovered from any authors during scraping")

            # Update release schedules with all books (even if scraping found nothing)
            updated_schedules = self.update_release_schedules(
                existing_schedules, all_discovered_books
            )

            # Send notifications (before cleanup to avoid data loss on failure)
            # This includes reminders and release day alerts for existing books
            self.send_notifications(updated_schedules, new_discoveries, date_changes)

            # Clean up old releases (after notifications, before save)
            self.cleanup_old_releases(updated_schedules)

            # Save updated schedules
            self.save_release_schedules(updated_schedules)
            
            logger.info("Monitoring cycle completed successfully")
            return True
            
        except Exception as e:
            error_msg = f"Book monitoring cycle failed: {str(e)}"
            logger.error(error_msg)
            
            # Send failure alert
            try:
                self.email_sender.send_tracker_failure_alert(error_msg)
            except Exception as email_error:
                logger.error(f"Failed to send failure alert: {email_error}")
            
            return False
    
    def load_authors(self) -> List[Dict]:
        """Load author configuration from YAML file."""
        
        try:
            if not os.path.exists(self.authors_file):
                logger.error(f"Authors file not found: {self.authors_file}")
                return []
            
            with open(self.authors_file, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                return data.get('authors', [])
                
        except Exception as e:
            logger.error(f"Error loading authors: {e}")
            return []
    
    def load_release_schedules(self) -> Dict:
        """Load existing release schedules from JSON file."""
        
        try:
            if not os.path.exists(self.schedules_file):
                logger.info(f"Schedules file not found, starting fresh: {self.schedules_file}")
                return {'books': [], 'last_updated': datetime.now().isoformat()}
            
            with open(self.schedules_file, 'r', encoding='utf-8') as file:
                return json.load(file)
                
        except Exception as e:
            logger.error(f"Error loading release schedules: {e}")
            return {'books': [], 'last_updated': datetime.now().isoformat()}
    
    def save_release_schedules(self, schedules: Dict) -> bool:
        """Save release schedules to JSON file."""
        
        try:
            schedules['last_updated'] = datetime.now().isoformat()
            
            with open(self.schedules_file, 'w', encoding='utf-8') as file:
                json.dump(schedules, file, indent=2, default=str)
                
            logger.info(f"Release schedules saved to {self.schedules_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving release schedules: {e}")
            return False
    
    def find_existing_book(self, book: Dict, existing_schedules: Dict) -> Optional[Dict]:
        """Find existing book in schedules by ID or title/author match."""
        
        existing_books = existing_schedules.get('books', [])
        
        # First try to match by ID
        book_id = book.get('id')
        if book_id:
            for existing in existing_books:
                if existing.get('id') == book_id:
                    return existing
        
        # Fallback to title/author match
        book_title = book.get('title', '').lower()
        book_author = book.get('author', '').lower()
        
        for existing in existing_books:
            existing_title = existing.get('title', '').lower()
            existing_author = existing.get('author', '').lower()
            
            if book_title == existing_title and book_author == existing_author:
                return existing
        
        return None

    def _find_book_by_id(self, schedules: Dict, book_id: str) -> Optional[Dict]:
        """Find a book in schedules by ID."""
        for book in schedules.get('books', []):
            if book.get('id') == book_id:
                return book
        return None

    def has_date_changed(self, new_book: Dict, existing_book: Dict) -> bool:
        """Check if release date has changed between versions."""

        new_date = new_book.get('release_date')
        existing_date = existing_book.get('release_date')

        # Convert to comparable format
        new_date_str = str(new_date) if new_date else ""
        existing_date_str = str(existing_date) if existing_date else ""

        return new_date_str != existing_date_str

    def _parse_date_field(self, date_value) -> Optional[date]:
        """
        Parse a date field that could be a string, date object, or other type.

        Args:
            date_value: Date value in various formats (str, date, datetime, or other)

        Returns:
            date object or None if parsing fails
        """
        if not date_value:
            return None

        try:
            if isinstance(date_value, str):
                return datetime.fromisoformat(date_value.replace('Z', '+00:00')).date()
            elif isinstance(date_value, datetime):
                # Check datetime BEFORE date (datetime is a subclass of date)
                return date_value.date()
            elif isinstance(date_value, date):
                return date_value
            else:
                return None
        except Exception as e:
            logger.warning(f"Could not parse date value: {date_value} - {e}")
            return None

    def _update_book_status(self, book: Dict) -> None:
        """Update book status to 'released' if release date has passed."""

        release_date = book.get('release_date')
        release_date_obj = self._parse_date_field(release_date)

        if release_date_obj and release_date_obj <= date.today():
            book['status'] = 'released'

    def update_release_schedules(self, existing_schedules: Dict, new_books: List[Dict]) -> Dict:
        """
        Update release schedules with new book data.

        Uses dictionary-based lookup for O(n) performance instead of nested loops O(n*m).
        """

        existing_books = existing_schedules.get('books', [])

        # Create indexes for O(1) lookup:
        # 1. Index by book ID
        # 2. Index by (title, author) tuple for fallback matching
        existing_by_id = {}
        existing_by_title_author = {}

        for existing in existing_books:
            book_id = existing.get('id')
            if book_id:
                existing_by_id[book_id] = existing

            # Also index by title+author for fallback matching
            title = existing.get('title', '').lower()
            author = existing.get('author', '').lower()
            if title and author:
                existing_by_title_author[(title, author)] = existing

        # Track which existing books have been matched/updated
        updated_book_ids = set()
        final_books = []

        # Process new books: update existing or add as new
        for new_book in new_books:
            new_id = new_book.get('id')
            new_title = new_book.get('title', '').lower()
            new_author = new_book.get('author', '').lower()

            # Try to find matching existing book (by ID first, then title+author)
            existing = None
            if new_id and new_id in existing_by_id:
                existing = existing_by_id[new_id]
            elif (new_title, new_author) in existing_by_title_author:
                existing = existing_by_title_author[(new_title, new_author)]

            if existing:
                # Update existing book with new data (use deepcopy to avoid modifying original)
                updated_book = copy.deepcopy(existing)
                updated_book.update({
                    'title': new_book.get('title', existing.get('title')),
                    'release_date': new_book.get('release_date', existing.get('release_date')),
                    'source_url': new_book.get('source_url', existing.get('source_url')),
                    'last_checked': datetime.now().isoformat(),
                    'metadata': {**existing.get('metadata', {}), **new_book.get('metadata', {})}
                })
                final_books.append(updated_book)
                updated_book_ids.add(existing.get('id'))
            else:
                # Genuinely new book - add it
                final_books.append(new_book)

        # Add existing books that weren't matched with any new books
        for existing in existing_books:
            existing_id = existing.get('id')
            if existing_id not in updated_book_ids:
                # Keep existing book even if not found in new scrape (use deepcopy to avoid mutation)
                existing_copy = copy.deepcopy(existing)
                existing_copy['last_checked'] = datetime.now().isoformat()
                final_books.append(existing_copy)

        # Update status for all books based on release dates
        for book in final_books:
            self._update_book_status(book)

        return {
            'books': final_books,
            'last_updated': datetime.now().isoformat()
        }
    
    def send_notifications(self, schedules: Dict, new_discoveries: List[Dict], date_changes: List[Dict]):
        """Send appropriate email notifications."""
        
        books = schedules.get('books', [])
        today = date.today()
        
        # New discovery notifications
        if new_discoveries:
            logger.info(f"Sending discovery notifications for {len(new_discoveries)} books")
            success = self.email_sender.send_book_discovery_alert(new_discoveries)
            if success:
                logger.info(f"Successfully sent discovery notifications")
                # Mark notifications as sent
                for book in new_discoveries:
                    # Find the book in updated schedules and add notification
                    book_to_update = self._find_book_by_id(schedules, book['id'])
                    if book_to_update:
                        book_to_update.setdefault('notifications_sent', []).append({
                            'type': 'discovery',
                            'date': datetime.now().isoformat()
                        })
                    else:
                        logger.warning(f"Could not find book {book['id']} in updated schedules to record notification")
            else:
                logger.error(f"Failed to send discovery notifications for {len(new_discoveries)} books")
        
        # Date change notifications (treat as new discovery)
        if date_changes:
            changed_books = [change['book'] for change in date_changes]
            logger.info(f"Sending date change notifications for {len(changed_books)} books")
            success = self.email_sender.send_book_discovery_alert(changed_books)
            if success:
                logger.info(f"Successfully sent date change notifications")
                for change in date_changes:
                    # Find the book in updated schedules and add notification
                    book_to_update = self._find_book_by_id(schedules, change['book']['id'])
                    if book_to_update:
                        book_to_update.setdefault('notifications_sent', []).append({
                            'type': 'date_change',
                            'date': datetime.now().isoformat(),
                            'old_date': str(change.get('old_date', '')),
                            'new_date': str(change.get('new_date', ''))
                        })
                    else:
                        logger.warning(f"Could not find book {change['book']['id']} in updated schedules to record notification")
            else:
                logger.error(f"Failed to send date change notifications for {len(changed_books)} books")
        
        # 7-day reminders
        reminder_books = []
        for book in books:
            if self.should_send_reminder(book, today):
                reminder_books.append(book)
        
        if reminder_books:
            logger.info(f"Sending 7-day reminders for {len(reminder_books)} books")
            success = self.email_sender.send_release_reminder(reminder_books)
            if success:
                logger.info(f"Successfully sent 7-day reminder notifications")
                for book in reminder_books:
                    # Find the book in updated schedules and add notification
                    book_to_update = self._find_book_by_id(schedules, book['id'])
                    if book_to_update:
                        book_to_update.setdefault('notifications_sent', []).append({
                            'type': 'reminder',
                            'date': datetime.now().isoformat()
                        })
                    else:
                        logger.warning(f"Could not find book {book['id']} in updated schedules to record notification")
            else:
                logger.error(f"Failed to send 7-day reminder notifications for {len(reminder_books)} books")
        
        # Release day notifications
        release_day_books = []
        for book in books:
            if self.should_send_release_day_alert(book, today):
                release_day_books.append(book)
        
        if release_day_books:
            logger.info(f"Sending release day alerts for {len(release_day_books)} books")
            success = self.email_sender.send_release_day_alert(release_day_books)
            if success:
                logger.info(f"Successfully sent release day notifications")
                for book in release_day_books:
                    # Find the book in updated schedules and add notification
                    book_to_update = self._find_book_by_id(schedules, book['id'])
                    if book_to_update:
                        book_to_update.setdefault('notifications_sent', []).append({
                            'type': 'release_day',
                            'date': datetime.now().isoformat()
                        })
                    else:
                        logger.warning(f"Could not find book {book['id']} in updated schedules to record notification")
            else:
                logger.error(f"Failed to send release day notifications for {len(release_day_books)} books")
    
    def should_send_reminder(self, book: Dict, today: date) -> bool:
        """Check if 7-day reminder should be sent for book."""

        release_date = book.get('release_date')
        release_date_obj = self._parse_date_field(release_date)

        if not release_date_obj:
            return False

        # Check if 7 days before release
        reminder_date = release_date_obj - timedelta(days=7)
        if today != reminder_date:
            return False

        # Check if reminder already sent
        notifications = book.get('notifications_sent', [])
        for notification in notifications:
            if notification.get('type') == 'reminder':
                return False

        return True
    
    def should_send_release_day_alert(self, book: Dict, today: date) -> bool:
        """Check if release day alert should be sent for book."""

        release_date = book.get('release_date')
        release_date_obj = self._parse_date_field(release_date)

        if not release_date_obj:
            return False

        # Check if it's release day
        if today != release_date_obj:
            return False

        # Check if release day alert already sent
        notifications = book.get('notifications_sent', [])
        for notification in notifications:
            if notification.get('type') == 'release_day':
                return False

        return True
    
    def cleanup_old_releases(self, schedules: Dict):
        """Remove books released more than 6 months ago."""

        cutoff_date = date.today() - timedelta(days=180)  # 6 months
        books = schedules.get('books', [])

        books_to_keep = []
        removed_count = 0

        for book in books:
            release_date = book.get('release_date')
            release_date_obj = self._parse_date_field(release_date)

            # Remove if release date is valid and older than cutoff
            if release_date_obj and release_date_obj < cutoff_date:
                removed_count += 1
                logger.info(f"Removing old release: {book.get('title')} by {book.get('author')} (released {release_date_obj})")
            else:
                # Keep books with no date, unparseable dates, or recent releases
                books_to_keep.append(book)

        if removed_count > 0:
            schedules['books'] = books_to_keep
            logger.info(f"Cleaned up {removed_count} old releases")

def main():
    """Main entry point for book monitoring."""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('book_monitor.log')
        ]
    )
    
    logger.info("Book Release Tracker starting up")
    
    try:
        monitor = BookMonitor()
        success = monitor.run_monitoring_cycle()
        
        if success:
            logger.info("Book monitoring completed successfully")
            sys.exit(0)
        else:
            logger.error("Book monitoring failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error in book monitoring: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()