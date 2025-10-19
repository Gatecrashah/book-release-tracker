#!/usr/bin/env python3
"""
Email template system for book release notifications
Centralized HTML generation for book release alerts
"""

from typing import Dict, List
from datetime import datetime, date

class EmailTemplates:
    """Centralized email template manager for book releases"""

    # Notification type configurations
    NOTIFICATION_CONFIGS = {
        'discovery': {
            'subject_emoji': '📚',
            'subject_template': '{count} new {plural} discovered!',
            'header_title': '📚 New Book Release Alert!',
            'header_subtitle': '{count} new {plural} discovered from your favorite authors',
            'footer_message': 'Stay tuned for more release updates! 📖',
            'css_class': 'new-release',
            'badge_class': 'type-discovery',
            'badge_text': 'NEW DISCOVERY',
            'icon': '📚'
        },
        'reminder': {
            'subject_emoji': '📅',
            'subject_template': '{count} {plural} releasing in 7 days!',
            'header_title': '📅 Release Reminder',
            'header_subtitle': '{count} {plural} from your favorite authors releasing in 7 days!',
            'footer_message': "Don't forget to pre-order! 📚",
            'css_class': 'release-reminder',
            'badge_class': 'type-reminder',
            'badge_text': '7-DAY REMINDER',
            'icon': '📅'
        },
        'release': {
            'subject_emoji': '🎉',
            'subject_template': '{count} {plural} available now!',
            'header_title': '🎉 Release Day!',
            'header_subtitle': '{count} {plural} from your favorite authors available now!',
            'footer_message': 'Happy reading! 📖',
            'css_class': 'release-day',
            'badge_class': 'type-release',
            'badge_text': 'OUT TODAY!',
            'icon': '🎉'
        }
    }

    @staticmethod
    def get_base_styles() -> str:
        """Common CSS styles for all email templates"""
        return """
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        .header { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; }
        .book-section { 
            margin: 25px 0; 
            border: 2px solid #ecf0f1; 
            border-radius: 10px; 
            padding: 20px; 
            background-color: #fdfdfe; 
        }
        .book { 
            background-color: #f8f9fa; 
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 8px; 
            border-left: 4px solid #3498db; 
        }
        .new-release { border-left-color: #27ae60; background-color: #f0f9f4; }
        .release-reminder { border-left-color: #f39c12; background-color: #fef9e7; }
        .release-day { border-left-color: #e74c3c; background-color: #fdf2f2; }
        .title { font-size: 20px; font-weight: bold; margin: 10px 0; color: #2c3e50; }
        .author { font-size: 16px; color: #7f8c8d; margin-bottom: 10px; }
        .release-date { 
            font-size: 18px; 
            font-weight: bold; 
            margin: 10px 0; 
            padding: 8px 12px; 
            background-color: #e8f4fd; 
            border-radius: 4px; 
            border-left: 3px solid #3498db;
        }
        .series { color: #9b59b6; font-style: italic; margin-bottom: 8px; }
        .footer { 
            margin-top: 30px; 
            padding-top: 20px; 
            border-top: 1px solid #bdc3c7; 
            color: #7f8c8d; 
            font-size: 12px; 
        }
        .notification-type { 
            display: inline-block; 
            padding: 6px 12px; 
            border-radius: 20px; 
            font-size: 12px; 
            font-weight: bold; 
            margin-bottom: 10px; 
        }
        .type-discovery { background-color: #d5f4e6; color: #27ae60; }
        .type-reminder { background-color: #fef3cd; color: #f39c12; }
        .type-release { background-color: #f8d7da; color: #721c24; }
        """
    
    @classmethod
    def format_book_notification(cls, book: Dict, notification_type: str) -> str:
        """Format individual book notification for email"""
        title = book.get('title', 'Unknown Title')
        author = book.get('author', 'Unknown Author')
        release_date = book.get('release_date')
        series = book.get('metadata', {}).get('series', '')
        source_url = book.get('source_url', '')
        
        # Format release date
        date_str = ""
        if release_date:
            if isinstance(release_date, str):
                date_str = release_date
            elif isinstance(release_date, date):
                date_str = release_date.strftime("%B %d, %Y")
        
        # Determine CSS class and icon based on notification type
        css_class = {
            'discovery': 'new-release',
            'reminder': 'release-reminder',
            'release': 'release-day'
        }.get(notification_type, 'book')
        
        icon = {
            'discovery': '📚',
            'reminder': '📅',
            'release': '🎉'
        }.get(notification_type, '📖')
        
        type_class = {
            'discovery': 'type-discovery',
            'reminder': 'type-reminder',
            'release': 'type-release'
        }.get(notification_type, 'type-discovery')
        
        type_text = {
            'discovery': 'NEW DISCOVERY',
            'reminder': '7-DAY REMINDER',
            'release': 'OUT TODAY!'
        }.get(notification_type, 'NOTIFICATION')
        
        book_html = f"""
        <div class="book {css_class}">
            <div class="notification-type {type_class}">{type_text}</div>
            <div class="title">{icon} {title}</div>
            <div class="author">by {author}</div>
        """
        
        # Add series if available
        if series:
            book_html += f'<div class="series">📖 Series: {series}</div>'
        
        # Add release date
        if date_str:
            book_html += f'<div class="release-date">📅 Release Date: {date_str}</div>'
        
        # Add source link if available
        if source_url:
            book_html += f"""
            <div style="margin-top: 15px; font-size: 12px; color: #7f8c8d;">
                <strong>Source:</strong> <a href="{source_url}" style="color: #3498db;">{source_url}</a>
            </div>
            """
        
        book_html += "</div>"

        return book_html

    @classmethod
    def create_book_notification_email(cls, books: List[Dict], notification_type: str) -> str:
        """
        Unified method to create email for book notifications.

        Args:
            books: List of book dictionaries
            notification_type: Type of notification ('discovery', 'reminder', or 'release')

        Returns:
            HTML string for the email
        """
        if not books:
            return "No books to display."

        # Get configuration for this notification type
        config = cls.NOTIFICATION_CONFIGS.get(notification_type)
        if not config:
            raise ValueError(f"Unknown notification type: {notification_type}")

        # Calculate book count and plural
        book_count = len(books)
        plural = "book" if book_count == 1 else "books"

        # Build HTML email
        html_content = f"""
        <html>
        <head>
            <style>
                {cls.get_base_styles()}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{config['header_title']}</h1>
                <p>{config['header_subtitle'].format(count=book_count, plural=plural)}</p>
            </div>
        """

        # Add each book
        for book in books:
            html_content += cls.format_book_notification(book, notification_type)

        # Add footer
        html_content += f"""
            <div class="footer">
                <p><strong>🤖 Automated by your Book Release Tracker</strong></p>
                <p>{config['footer_message']}</p>
                <p><em>Powered by Resend API</em></p>
            </div>
        </body>
        </html>
        """

        return html_content

    @classmethod
    def create_book_discovery_email(cls, books: List[Dict]) -> str:
        """Create email for newly discovered book releases"""
        return cls.create_book_notification_email(books, 'discovery')
    
    @classmethod
    def create_release_reminder_email(cls, books: List[Dict]) -> str:
        """Create email for 7-day release reminders"""
        return cls.create_book_notification_email(books, 'reminder')
    
    @classmethod
    def create_release_day_email(cls, books: List[Dict]) -> str:
        """Create email for release day notifications"""
        return cls.create_book_notification_email(books, 'release')
    
    @classmethod
    def create_failure_alert_email(cls, error_details: str) -> str:
        """Create scraper failure alert email HTML"""
        
        html_content = f"""
        <html>
        <head>
            <style>
                {cls.get_base_styles()}
            </style>
        </head>
        <body>
            <div style="background-color: #fdf2f2; border-left: 4px solid #e74c3c; padding: 20px; margin: 15px 0; border-radius: 8px;">
                <h2 style="color: #e74c3c;">🚨 Book Tracker Alert</h2>
                <p><strong>Your book release tracker has encountered an error!</strong></p>
                <div style="background-color: #fff; padding: 15px; border-radius: 4px; margin: 10px 0;">
                    <h3>Error Details:</h3>
                    <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto;">{error_details}</pre>
                </div>
                <h3>Possible Causes:</h3>
                <ul>
                    <li>🔗 Author pages have changed</li>
                    <li>🏗️ Website structure updated</li>
                    <li>🛡️ Anti-bot measures blocking access</li>
                    <li>📚 Book data format changed</li>
                    <li>🌐 Network connectivity issues</li>
                </ul>
                <h3>Recommended Actions:</h3>
                <ol>
                    <li>Check if author pages are still accessible</li>
                    <li>Verify the scraper configuration</li>
                    <li>Check GitHub Actions logs for detailed error messages</li>
                    <li>Update the scraper if needed</li>
                </ol>
            </div>
            <div class="footer">
                <p><strong>🤖 Automated alert from your Book Release Tracker</strong></p>
                <p><em>Powered by Resend API</em></p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    @classmethod
    def create_test_email(cls) -> str:
        """Create test email HTML"""
        
        html_content = f"""
        <html>
        <head>
            <style>
                {cls.get_base_styles()}
            </style>
        </head>
        <body>
            <h2>✅ Test Email Successful!</h2>
            <p>This is a test email from your Book Release Tracker.</p>
            <p><strong>Configuration is working correctly!</strong></p>
            <hr>
            <p style="color: #7f8c8d; font-size: 12px;">
                Powered by Resend API 🚀
            </p>
        </body>
        </html>
        """
        
        return html_content