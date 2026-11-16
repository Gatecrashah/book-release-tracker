#!/usr/bin/env python3
"""
Email notification system for book release alerts using Resend API
"""

import requests
import os
import sys
from typing import Dict, List
import logging
from email_templates import EmailTemplates

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        # Get Resend API configuration from environment variables
        self.api_key = os.getenv('RESEND_API_KEY')
        self.email_to = os.getenv('EMAIL_TO')
        self.api_url = 'https://api.resend.com/emails'
        
        if not self.api_key:
            raise ValueError("RESEND_API_KEY environment variable is required")
        if not self.email_to:
            raise ValueError("EMAIL_TO environment variable is required")

    def send_book_notification(self, books: List[Dict], notification_type: str) -> None:
        """
        Unified method to send book notification emails.

        Args:
            books: List of book dictionaries
            notification_type: Type of notification ('discovery', 'reminder', or 'release')

        Raises:
            ValueError: for an unknown notification type
            RuntimeError, requests.RequestException: if the email could not be sent
        """
        if not books:
            logger.info(f"No books for {notification_type} notification")
            return

        config = EmailTemplates.NOTIFICATION_CONFIGS.get(notification_type)
        if not config:
            raise ValueError(f"Unknown notification type: {notification_type}")

        book_count = len(books)
        plural = "book" if book_count == 1 else "books"
        subject = f"{config['subject_emoji']} {config['subject_template'].format(count=book_count, plural=plural)}"
        html_content = EmailTemplates.create_book_notification_email(books, notification_type)

        self._send_email(subject, html_content, config.get('log_name', notification_type.title()))

    def send_book_discovery_alert(self, books: List[Dict]) -> None:
        """Send email notification about newly discovered books"""
        self.send_book_notification(books, 'discovery')

    def send_release_reminder(self, books: List[Dict]) -> None:
        """Send email notification for 7-day release reminders"""
        self.send_book_notification(books, 'reminder')

    def send_release_day_alert(self, books: List[Dict]) -> None:
        """Send email notification for books releasing today"""
        self.send_book_notification(books, 'release')

    def send_tracker_failure_alert(self, error_details: str) -> None:
        """Send email notification when tracker fails"""
        html_content = EmailTemplates.create_failure_alert_email(error_details)
        self._send_email("🚨 Book Tracker Failure Alert - Action Required", html_content, "Tracker Failure")

    def send_test_email(self) -> None:
        """Send a test email to verify Resend configuration"""
        self._send_email("📚 Test Email - Book Release Tracker", EmailTemplates.create_test_email(), "Test")

    def _send_email(self, subject: str, html_content: str, email_type: str) -> None:
        """Send an email via the Resend API, raising if it is not accepted."""
        payload = {
            "from": "Book Release Tracker <onboarding@resend.dev>",
            "to": [self.email_to],
            "subject": subject,
            "html": html_content
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(
                f"Resend rejected {email_type} email (status {response.status_code}): {response.text}"
            )

        email_id = response.json().get('id', 'unknown')
        logger.info(f"{email_type} email sent successfully to {self.email_to} (ID: {email_id})")

def main():
    """Test the email sender"""
    logging.basicConfig(level=logging.INFO)

    sample_books = [
        {
            'id': 'sanderson_tailored_realities_2025',
            'title': 'Tailored Realities',
            'author': 'Brandon Sanderson',
            'release_date': '2025-12-09',
            'source_url': 'https://www.booknotification.com/authors/brandon-sanderson',
            'metadata': {
                'series': 'Standalone Collection',
                'publisher': 'Tor Books'
            }
        }
    ]

    try:
        email_sender = EmailSender()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nTo fix this, set the following environment variables:")
        print("export RESEND_API_KEY='your-resend-api-key'")
        print("export EMAIL_TO='your-email-address'")
        sys.exit(1)

    print("Testing Book Release Tracker email configuration...")
    email_sender.send_test_email()
    print("✅ Test email sent successfully!")

    print("Sending sample book discovery alert...")
    email_sender.send_book_discovery_alert(sample_books)
    print("✅ Sample book discovery alert sent successfully!")
    print("Check your email inbox!")

if __name__ == "__main__":
    main()