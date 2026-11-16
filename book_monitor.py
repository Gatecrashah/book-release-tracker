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

# A book the source stopped listing this long ago is treated as withdrawn or renamed.
# The window absorbs a few failed scrapes and the source dropping a book on release day.
STALE_AFTER = timedelta(days=3)

# Alerts are due anywhere inside these windows, so a skipped or failed run is caught up by the next one.
REMINDER_WINDOW = timedelta(days=7)
RELEASE_ALERT_WINDOW = timedelta(days=3)

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
            scrape_failures = []
            for author in authors:
                if author.get('status') != 'active':
                    continue

                logger.info(f"Scraping releases for {author['name']}")
                try:
                    books = self.scraper.scrape_author_releases(author)
                except Exception as e:
                    logger.error(f"Scraping failed for {author['name']}: {e}")
                    scrape_failures.append(f"{author['name']}: {e}")
                    continue
                all_discovered_books.extend(books)

            existing_by_id = {book['id']: book for book in existing_schedules.get('books', [])}
            scraped_by_id = {book['id']: book for book in all_discovered_books}

            new_discoveries = []
            date_changes = []
            for book_id, book in scraped_by_id.items():
                existing_book = existing_by_id.get(book_id)
                if not existing_book:
                    new_discoveries.append(book)
                    logger.info(f"New book discovered: {book['title']} by {book['author']}")
                elif self.has_date_changed(book, existing_book):
                    date_changes.append({
                        'book': book,
                        'old_date': existing_book.get('release_date'),
                        'new_date': book.get('release_date')
                    })
                    logger.info(f"Release date changed for: {book['title']}")

            updated_schedules = self.update_release_schedules(
                existing_schedules, list(scraped_by_id.values())
            )

            # Send notifications (before cleanup to avoid data loss on failure)
            # This includes reminders and release day alerts for existing books
            self.send_notifications(updated_schedules, new_discoveries, date_changes)

            # Clean up old releases (after notifications, before save)
            self.cleanup_old_releases(updated_schedules)

            # Save updated schedules
            self.save_release_schedules(updated_schedules)

            if scrape_failures:
                raise RuntimeError("Scraping failed for " + "; ".join(scrape_failures))

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
        
        if not os.path.exists(self.schedules_file):
            logger.info(f"Schedules file not found, starting fresh: {self.schedules_file}")
            return {'books': [], 'last_updated': datetime.now().isoformat()}

        with open(self.schedules_file, 'r', encoding='utf-8') as file:
            schedules = json.load(file)

        # IDs are derived from author and title, so files written with an older ID scheme still match.
        for book in schedules.get('books', []):
            book['id'] = self.scraper.generate_book_id(book['title'], book['author'])
        return schedules

    def save_release_schedules(self, schedules: Dict) -> None:
        """Save release schedules to JSON file."""

        schedules['last_updated'] = datetime.now().isoformat()

        with open(self.schedules_file, 'w', encoding='utf-8') as file:
            json.dump(schedules, file, indent=2, default=str)

        logger.info(f"Release schedules saved to {self.schedules_file}")
    
    def _find_book_by_id(self, schedules: Dict, book_id: str) -> Optional[Dict]:
        """Find a book in schedules by ID."""
        for book in schedules.get('books', []):
            if book.get('id') == book_id:
                return book
        return None

    def _record_notification(self, schedules: Dict, book_id: str, notification_type: str, **extra_fields) -> None:
        """
        Record a notification as sent for a book.

        Args:
            schedules: The schedules dictionary containing books
            book_id: ID of the book to record notification for
            notification_type: Type of notification (e.g., 'discovery', 'reminder', 'release_day', 'date_change')
            **extra_fields: Additional fields to include in the notification record (e.g., old_date, new_date)
        """
        book_to_update = self._find_book_by_id(schedules, book_id)
        if book_to_update:
            notification_record = {
                'type': notification_type,
                'date': datetime.now().isoformat(),
                **extra_fields
            }
            book_to_update.setdefault('notifications_sent', []).append(notification_record)
        else:
            logger.warning(f"Could not find book {book_id} in updated schedules to record notification")

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
        """Update book status based on release date."""

        release_date = book.get('release_date')
        release_date_obj = self._parse_date_field(release_date)

        if release_date_obj:
            if release_date_obj <= date.today():
                book['status'] = 'released'
            else:
                book['status'] = 'upcoming'
        # If release_date_obj is None, keep existing status unchanged

    def update_release_schedules(self, existing_schedules: Dict, new_books: List[Dict]) -> Dict:
        """Merge freshly scraped books into the stored schedules, matching on book ID."""

        books_by_id = {
            book['id']: copy.deepcopy(book) for book in existing_schedules.get('books', [])
        }

        for new_book in new_books:
            existing = books_by_id.get(new_book['id'])
            if existing:
                existing.update({
                    'title': new_book['title'],
                    'release_date': new_book['release_date'],
                    'source_url': new_book['source_url'],
                    'last_checked': datetime.now().isoformat(),
                    'metadata': {**existing.get('metadata', {}), **new_book.get('metadata', {})}
                })
            else:
                books_by_id[new_book['id']] = new_book

        final_books = list(books_by_id.values())
        for book in final_books:
            self._update_book_status(book)

        return {
            'books': final_books,
            'last_updated': datetime.now().isoformat()
        }

    def send_notifications(self, schedules: Dict, new_discoveries: List[Dict], date_changes: List[Dict]):
        """Send appropriate email notifications. Raises if any email fails to send."""
        
        books = schedules.get('books', [])
        today = date.today()
        
        # New discovery notifications
        if new_discoveries:
            logger.info(f"Sending discovery notifications for {len(new_discoveries)} books")
            self.email_sender.send_book_discovery_alert(new_discoveries)
            for book in new_discoveries:
                self._record_notification(schedules, book['id'], 'discovery')
        
        # Date change notifications (treat as new discovery)
        if date_changes:
            changed_books = [change['book'] for change in date_changes]
            logger.info(f"Sending date change notifications for {len(changed_books)} books")
            self.email_sender.send_book_discovery_alert(changed_books)
            for change in date_changes:
                self._record_notification(
                    schedules,
                    change['book']['id'],
                    'date_change',
                    old_date=str(change.get('old_date', '')),
                    new_date=str(change.get('new_date', ''))
                )
        
        # Release reminders
        reminder_books = []
        for book in books:
            if self.should_send_reminder(book, today):
                reminder_books.append(book)
        
        if reminder_books:
            logger.info(f"Sending release reminders for {len(reminder_books)} books")
            self.email_sender.send_release_reminder(reminder_books)
            for book in reminder_books:
                self._record_notification(schedules, book['id'], 'reminder')
        
        # Release alerts
        release_day_books = []
        for book in books:
            if self.should_send_release_day_alert(book, today):
                release_day_books.append(book)
        
        if release_day_books:
            logger.info(f"Sending release day alerts for {len(release_day_books)} books")
            self.email_sender.send_release_day_alert(release_day_books)
            for book in release_day_books:
                self._record_notification(schedules, book['id'], 'release_day')
    
    def _still_listed(self, book: Dict, today: date, release_date: date) -> bool:
        """Whether the source listed this book within STALE_AFTER of today, or of its release if that has passed."""
        last_seen = self._parse_date_field(book.get('last_checked'))
        return last_seen is not None and min(today, release_date) - last_seen <= STALE_AFTER

    def _notified_since(self, book: Dict, since: date, notification_type: Optional[str] = None) -> bool:
        """Whether a notification (of the given type, or any type) was sent for this book on or after a date."""
        for notification in book.get('notifications_sent', []):
            sent = self._parse_date_field(notification.get('date'))
            if sent and sent >= since and notification_type in (None, notification.get('type')):
                return True
        return False

    def should_send_reminder(self, book: Dict, today: date) -> bool:
        """
        A reminder is due during the week before release, unless an email about the book
        (discovery, date change or reminder) already went out within that week.
        """
        release_date = self._parse_date_field(book.get('release_date'))
        if not release_date or not self._still_listed(book, today, release_date):
            return False

        window_start = release_date - REMINDER_WINDOW
        return window_start <= today < release_date and not self._notified_since(book, window_start)

    def should_send_release_day_alert(self, book: Dict, today: date) -> bool:
        """A release alert is due from release day until RELEASE_ALERT_WINDOW later, once per release date."""
        release_date = self._parse_date_field(book.get('release_date'))
        if not release_date or not self._still_listed(book, today, release_date):
            return False

        in_window = release_date <= today <= release_date + RELEASE_ALERT_WINDOW
        return in_window and not self._notified_since(book, release_date, 'release_day')

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