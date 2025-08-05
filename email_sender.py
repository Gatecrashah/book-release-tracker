#!/usr/bin/env python3
"""
Email notification system for book release alerts using Resend API
"""

import requests
import os
import json
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
    
    def send_book_discovery_alert(self, books: List[Dict]) -> bool:
        """Send email notification about newly discovered books"""
        
        if not books:
            logger.info("No new books to report")
            return True
        
        try:
            book_count = len(books)
            plural = "book" if book_count == 1 else "books"
            
            # Create subject based on number of books
            subject = f"📚 {book_count} new {plural} discovered!"
            
            # Create HTML content
            html_content = EmailTemplates.create_book_discovery_email(books)
            
            return self._send_email(subject, html_content, "Book Discovery")
            
        except Exception as e:
            logger.error(f"Failed to send book discovery alert: {e}")
            return False
    
    def send_release_reminder(self, books: List[Dict]) -> bool:
        """Send email notification for 7-day release reminders"""
        
        if not books:
            logger.info("No release reminders to send")
            return True
        
        try:
            book_count = len(books)
            plural = "book" if book_count == 1 else "books"
            
            subject = f"📅 {book_count} {plural} releasing in 7 days!"
            
            # Create HTML content
            html_content = EmailTemplates.create_release_reminder_email(books)
            
            return self._send_email(subject, html_content, "Release Reminder")
            
        except Exception as e:
            logger.error(f"Failed to send release reminder: {e}")
            return False
    
    def send_release_day_alert(self, books: List[Dict]) -> bool:
        """Send email notification for books releasing today"""
        
        if not books:
            logger.info("No books releasing today")
            return True
        
        try:
            book_count = len(books)
            plural = "book" if book_count == 1 else "books"
            
            subject = f"🎉 {book_count} {plural} available now!"
            
            # Create HTML content
            html_content = EmailTemplates.create_release_day_email(books)
            
            return self._send_email(subject, html_content, "Release Day")
            
        except Exception as e:
            logger.error(f"Failed to send release day alert: {e}")
            return False
    
    def send_tracker_failure_alert(self, error_details: str) -> bool:
        """Send email notification when tracker fails"""
        
        try:
            html_content = EmailTemplates.create_failure_alert_email(error_details)
            subject = "🚨 Book Tracker Failure Alert - Action Required"
            
            return self._send_email(subject, html_content, "Tracker Failure")
            
        except Exception as e:
            logger.error(f"Failed to send tracker failure alert: {e}")
            return False
    
    def send_test_email(self) -> bool:
        """Send a test email to verify Resend configuration"""
        
        try:
            html_content = EmailTemplates.create_test_email()
            subject = "📚 Test Email - Book Release Tracker"
            
            return self._send_email(subject, html_content, "Test")
            
        except Exception as e:
            logger.error(f"Failed to send test email: {e}")
            return False
    
    def _send_email(self, subject: str, html_content: str, email_type: str) -> bool:
        """Internal method to send email via Resend API"""
        
        try:
            # Prepare the email payload for Resend API
            payload = {
                "from": "Book Release Tracker <onboarding@resend.dev>",
                "to": [self.email_to],
                "subject": subject,
                "html": html_content
            }
            
            # Send email via Resend API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.api_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                email_id = result.get('id', 'unknown')
                logger.info(f"{email_type} email sent successfully to {self.email_to} (ID: {email_id})")
                return True
            else:
                logger.error(f"Failed to send {email_type} email. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send {email_type} email: {e}")
            return False

def main():
    """Test the email sender"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Create sample book data for testing
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
        print("Testing Book Release Tracker email configuration...")
        
        # Send test email
        if email_sender.send_test_email():
            print("✅ Test email sent successfully!")
            
            # Send sample book discovery alert
            print("Sending sample book discovery alert...")
            if email_sender.send_book_discovery_alert(sample_books):
                print("✅ Sample book discovery alert sent successfully!")
                print("Check your email inbox!")
            else:
                print("❌ Failed to send sample book discovery alert")
        else:
            print("❌ Failed to send test email")
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nTo fix this, set the following environment variables:")
        print("export RESEND_API_KEY='your-resend-api-key'")
        print("export EMAIL_TO='your-email-address'")

if __name__ == "__main__":
    main()