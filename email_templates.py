#!/usr/bin/env python3
"""
Email template system for book release notifications
Centralized HTML generation for book release alerts

Design: Editorial/Literary Magazine aesthetic with vintage bookstore charm
"""

from typing import Dict, List
from datetime import datetime
import html

class EmailTemplates:
    """Centralized email template manager for book releases"""

    # Notification type configurations
    NOTIFICATION_CONFIGS = {
        'discovery': {
            'subject_emoji': '📚',
            'subject_template': '{count} new {plural} discovered!',
            'header_title': 'New Discovery',
            'header_subtitle': '{count} new {plural} from your favorite authors',
            'footer_message': 'More literary adventures await.',
            'accent_color': '#2D5A4A',  # Forest green
            'accent_light': '#E8F0EC',
            'badge_text': 'NEW DISCOVERY',
            'icon': '◆',
            'log_name': 'Book Discovery'
        },
        'date_change': {
            'subject_emoji': '🗓️',
            'subject_template': 'Release date changed for {count} {plural}',
            'header_title': 'Date Changed',
            'header_subtitle': '{count} {plural} rescheduled',
            'footer_message': 'Adjust your calendar.',
            'accent_color': '#2F4A6B',  # Slate blue
            'accent_light': '#EAF0F6',
            'badge_text': 'NEW DATE',
            'icon': '◈',
            'log_name': 'Date Change'
        },
        'reminder': {
            'subject_emoji': '📅',
            'subject_template': '{count} {plural} releasing within a week!',
            'header_title': 'Release Reminder',
            'header_subtitle': '{count} {plural} arriving within a week',
            'footer_message': 'Mark your calendar.',
            'accent_color': '#8B6914',  # Amber gold
            'accent_light': '#FBF6E9',
            'badge_text': 'THIS WEEK',
            'icon': '◇',
            'log_name': 'Release Reminder'
        },
        'release': {
            'subject_emoji': '🎉',
            'subject_template': '{count} {plural} available now!',
            'header_title': 'Available Now',
            'header_subtitle': '{count} {plural} ready for your reading list',
            'footer_message': 'Happy reading.',
            'accent_color': '#8B1538',  # Burgundy
            'accent_light': '#FAF0F2',
            'badge_text': 'OUT NOW',
            'icon': '★',
            'log_name': 'Release Day'
        }
    }

    @staticmethod
    def get_base_styles() -> str:
        """Common CSS styles for all email templates - Editorial/Literary aesthetic"""
        return """
        /* Reset and base */
        body {
            margin: 0;
            padding: 0;
            background-color: #F5F1EB;
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1.7;
            color: #2C2C2C;
            -webkit-font-smoothing: antialiased;
        }

        /* Container */
        .email-wrapper {
            max-width: 600px;
            margin: 0 auto;
            background-color: #FFFDF9;
            border: 1px solid #E8E4DC;
        }

        /* Masthead - solid fallback for email clients that don't support gradients */
        .masthead {
            background-color: #2C2C2C;
            background: linear-gradient(135deg, #2C2C2C 0%, #3D3D3D 100%);
            padding: 32px 40px;
            text-align: center;
            border-bottom: 3px solid #C9A227;
        }

        .masthead-title {
            font-family: Georgia, serif;
            font-size: 11px;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: #C9A227;
            margin: 0 0 8px 0;
        }

        .masthead-logo {
            font-family: Georgia, serif;
            font-size: 28px;
            font-weight: normal;
            font-style: italic;
            color: #FFFDF9;
            margin: 0;
            letter-spacing: 1px;
        }

        /* Header section */
        .header {
            padding: 48px 40px 32px 40px;
            text-align: center;
            border-bottom: 1px solid #E8E4DC;
        }

        .header-icon {
            font-size: 32px;
            color: #C9A227;
            margin-bottom: 16px;
        }

        .header-title {
            font-family: Georgia, serif;
            font-size: 32px;
            font-weight: normal;
            color: #2C2C2C;
            margin: 0 0 12px 0;
            letter-spacing: -0.5px;
        }

        .header-subtitle {
            font-family: Georgia, serif;
            font-size: 16px;
            color: #6B6B6B;
            margin: 0;
            font-style: italic;
        }

        .header-date {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 11px;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #9B9B9B;
            margin-top: 20px;
        }

        /* Content area */
        .content {
            padding: 32px 40px;
        }

        /* Book card */
        .book-card {
            background-color: #FFFDF9;
            border: 1px solid #E8E4DC;
            margin-bottom: 24px;
            position: relative;
        }

        .book-card-accent {
            height: 4px;
            width: 100%;
        }

        .book-card-inner {
            padding: 28px 32px;
        }

        .book-badge {
            display: inline-block;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 10px;
            letter-spacing: 2px;
            text-transform: uppercase;
            padding: 6px 14px;
            margin-bottom: 16px;
            font-weight: 600;
        }

        .book-title {
            font-family: Georgia, serif;
            font-size: 24px;
            font-weight: normal;
            color: #2C2C2C;
            margin: 0 0 8px 0;
            line-height: 1.3;
        }

        .book-author {
            font-family: Georgia, serif;
            font-size: 15px;
            color: #6B6B6B;
            margin: 0 0 20px 0;
            font-style: italic;
        }

        .book-meta {
            border-top: 1px solid #E8E4DC;
            padding-top: 20px;
            margin-top: 20px;
        }

        .book-date-label {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 11px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: #9B9B9B;
            display: block;
            margin-bottom: 4px;
        }

        .book-date-value {
            font-family: Georgia, serif;
            font-size: 18px;
            color: #2C2C2C;
            font-weight: normal;
            display: block;
        }

        .book-source {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px dashed #E8E4DC;
        }

        .book-source-link {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 11px;
            color: #9B9B9B;
            text-decoration: none;
        }

        .book-source-link:hover {
            color: #6B6B6B;
        }

        /* Decorative divider */
        .divider {
            text-align: center;
            padding: 8px 0;
            color: #C9A227;
            font-size: 14px;
            letter-spacing: 8px;
        }

        /* Footer */
        .footer {
            background-color: #F9F7F3;
            padding: 32px 40px;
            text-align: center;
            border-top: 1px solid #E8E4DC;
        }

        .footer-message {
            font-family: Georgia, serif;
            font-size: 15px;
            font-style: italic;
            color: #6B6B6B;
            margin: 0 0 20px 0;
        }

        .footer-brand {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 10px;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #9B9B9B;
            margin: 0;
        }

        .footer-powered {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 10px;
            color: #BFBFBF;
            margin-top: 8px;
        }

        /* Alert styles */
        .alert-card {
            background-color: #FDF8F8;
            border: 1px solid #E8D4D4;
            border-left: 4px solid #8B1538;
            padding: 28px 32px;
            margin-bottom: 24px;
        }

        .alert-title {
            font-family: Georgia, serif;
            font-size: 20px;
            color: #8B1538;
            margin: 0 0 16px 0;
        }

        .alert-content {
            font-family: Georgia, serif;
            font-size: 15px;
            color: #4A4A4A;
            line-height: 1.7;
        }

        .alert-code {
            background-color: #2C2C2C;
            color: #E8E4DC;
            padding: 16px 20px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            line-height: 1.5;
            overflow-x: auto;
            margin: 16px 0;
            border-radius: 2px;
        }

        .alert-list {
            font-family: Georgia, serif;
            font-size: 14px;
            color: #4A4A4A;
            padding-left: 20px;
        }

        .alert-list li {
            margin-bottom: 8px;
        }
        """

    @staticmethod
    def _format_date(value) -> str:
        """Format a date, or an ISO date string as stored in the schedules file, for display."""
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return html.escape(value)
        return f"{value:%B} {value.day}, {value.year}"

    @classmethod
    def format_book_notification(cls, book: Dict, notification_type: str) -> str:
        """Format individual book notification for email"""
        # Escape all user-provided content to prevent XSS
        title = html.escape(book.get('title', 'Unknown Title'))
        author = html.escape(book.get('author', 'Unknown Author'))
        source_url = book.get('source_url', '')
        date_str = cls._format_date(book.get('release_date'))
        previous_date_str = cls._format_date(book.get('previous_release_date'))

        # Get configuration from NOTIFICATION_CONFIGS
        config = cls.NOTIFICATION_CONFIGS.get(notification_type, {})
        accent_color = config.get('accent_color', '#2D5A4A')
        accent_light = config.get('accent_light', '#E8F0EC')
        badge_text = config.get('badge_text', 'NOTIFICATION')

        book_html = f"""
        <div class="book-card">
            <div class="book-card-accent" style="background-color: {accent_color};"></div>
            <div class="book-card-inner">
                <span class="book-badge" style="background-color: {accent_light}; color: {accent_color};">{badge_text}</span>
                <h2 class="book-title">{title}</h2>
                <p class="book-author">by {author}</p>
        """

        # Meta section
        book_html += '<div class="book-meta">'

        # Add release date
        if date_str:
            book_html += f"""
                <div>
                    <span class="book-date-label">Release Date</span>
                    <span class="book-date-value">{date_str}</span>
                </div>
            """

        if previous_date_str:
            book_html += f"""
                <div style="margin-top: 12px;">
                    <span class="book-date-label">Previously</span>
                    <span class="book-date-value" style="font-size: 15px; color: #9B9B9B; text-decoration: line-through;">{previous_date_str}</span>
                </div>
            """

        book_html += '</div>'  # Close book-meta

        # Add source link if available
        if source_url:
            book_html += f"""
                <div class="book-source">
                    <a href="{html.escape(source_url)}" class="book-source-link">View source →</a>
                </div>
            """

        book_html += """
            </div>
        </div>
        """

        return book_html

    @classmethod
    def create_book_notification_email(cls, books: List[Dict], notification_type: str) -> str:
        """
        Unified method to create email for book notifications.

        Args:
            books: List of book dictionaries
            notification_type: A key of NOTIFICATION_CONFIGS

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

        # Current date for masthead
        current_date = datetime.now().strftime("%B %Y").upper()

        # Build HTML email
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{config['header_title']}</title>
            <style>
                {cls.get_base_styles()}
            </style>
        </head>
        <body>
            <div class="email-wrapper">
                <!-- Masthead -->
                <div class="masthead">
                    <p class="masthead-title">Your Personal</p>
                    <h1 class="masthead-logo">Book Release Tracker</h1>
                </div>

                <!-- Header -->
                <div class="header">
                    <div class="header-icon">{config['icon']}</div>
                    <h2 class="header-title">{config['header_title']}</h2>
                    <p class="header-subtitle">{config['header_subtitle'].format(count=book_count, plural=plural)}</p>
                    <p class="header-date">{current_date}</p>
                </div>

                <!-- Content -->
                <div class="content">
        """

        # Add each book
        for i, book in enumerate(books):
            html_content += cls.format_book_notification(book, notification_type)
            # Add decorative divider between books (except after last)
            if i < len(books) - 1:
                html_content += '<div class="divider">◆ ◆ ◆</div>'

        # Add footer
        html_content += f"""
                </div>

                <!-- Footer -->
                <div class="footer">
                    <p class="footer-message">{config['footer_message']}</p>
                    <p class="footer-brand">Automated by Book Release Tracker</p>
                    <p class="footer-powered">Powered by Resend</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html_content

    @classmethod
    def create_failure_alert_email(cls, error_details: str) -> str:
        """Create scraper failure alert email HTML"""

        current_date = datetime.now().strftime("%B %d, %Y")
        # Escape error details to prevent XSS
        safe_error_details = html.escape(error_details)

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Tracker Alert</title>
            <style>
                {cls.get_base_styles()}
            </style>
        </head>
        <body>
            <div class="email-wrapper">
                <!-- Masthead -->
                <div class="masthead" style="background: linear-gradient(135deg, #5C1A1A 0%, #3D1A1A 100%); border-bottom-color: #8B1538;">
                    <p class="masthead-title" style="color: #D4A0A0;">System Alert</p>
                    <h1 class="masthead-logo">Book Release Tracker</h1>
                </div>

                <!-- Header -->
                <div class="header">
                    <div class="header-icon" style="color: #8B1538;">⚠</div>
                    <h2 class="header-title">Action Required</h2>
                    <p class="header-subtitle">Your tracker encountered an issue</p>
                    <p class="header-date">{current_date}</p>
                </div>

                <!-- Content -->
                <div class="content">
                    <div class="alert-card">
                        <h3 class="alert-title">Error Details</h3>
                        <div class="alert-code">{safe_error_details}</div>
                    </div>

                    <div style="margin-bottom: 24px;">
                        <h4 style="font-family: Georgia, serif; font-size: 16px; color: #2C2C2C; margin: 0 0 16px 0;">Possible Causes</h4>
                        <ul class="alert-list">
                            <li>Author pages may have changed structure</li>
                            <li>Website updates affecting data extraction</li>
                            <li>Network connectivity issues</li>
                            <li>Anti-bot measures blocking access</li>
                        </ul>
                    </div>

                    <div>
                        <h4 style="font-family: Georgia, serif; font-size: 16px; color: #2C2C2C; margin: 0 0 16px 0;">Recommended Actions</h4>
                        <ol class="alert-list">
                            <li>Verify author pages are accessible</li>
                            <li>Check GitHub Actions logs</li>
                            <li>Review scraper configuration</li>
                            <li>Update scraper if site structure changed</li>
                        </ol>
                    </div>
                </div>

                <!-- Footer -->
                <div class="footer">
                    <p class="footer-message">Automated system alert</p>
                    <p class="footer-brand">Book Release Tracker</p>
                    <p class="footer-powered">Powered by Resend</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html_content

    @classmethod
    def create_test_email(cls) -> str:
        """Create test email HTML"""

        current_date = datetime.now().strftime("%B %d, %Y")

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Test Email</title>
            <style>
                {cls.get_base_styles()}
            </style>
        </head>
        <body>
            <div class="email-wrapper">
                <!-- Masthead -->
                <div class="masthead">
                    <p class="masthead-title">Your Personal</p>
                    <h1 class="masthead-logo">Book Release Tracker</h1>
                </div>

                <!-- Header -->
                <div class="header">
                    <div class="header-icon" style="color: #2D5A4A;">✓</div>
                    <h2 class="header-title">Configuration Verified</h2>
                    <p class="header-subtitle">Your email setup is working correctly</p>
                    <p class="header-date">{current_date}</p>
                </div>

                <!-- Content -->
                <div class="content">
                    <div class="book-card">
                        <div class="book-card-accent" style="background-color: #2D5A4A;"></div>
                        <div class="book-card-inner" style="text-align: center; padding: 40px 32px;">
                            <p style="font-family: Georgia, serif; font-size: 18px; color: #2C2C2C; margin: 0 0 16px 0;">
                                Everything is set up and ready.
                            </p>
                            <p style="font-family: Georgia, serif; font-size: 15px; color: #6B6B6B; font-style: italic; margin: 0;">
                                You'll receive notifications when new books are discovered<br>
                                from your favorite authors.
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div class="footer">
                    <p class="footer-message">Happy reading ahead.</p>
                    <p class="footer-brand">Book Release Tracker</p>
                    <p class="footer-powered">Powered by Resend</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html_content
