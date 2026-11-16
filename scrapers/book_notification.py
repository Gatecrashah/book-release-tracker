#!/usr/bin/env python3
"""
Scraper for upcoming book releases on booknotification.com author pages.

Each author page has an FAQ entry "Are there upcoming new books by <author>?".
Its answer lists every upcoming book with the title in an <em> element:

    one book:   <author> has a new book coming out on <date> called <em>Title</em>.
    several:    <author> has N new books coming out: <em>Title</em> will be released on <date>. ...
    none:       <author> does not have any upcoming books with a set publication date ...

Some author pages have no such FAQ entry at all, which also means nothing is upcoming.
"""

import logging
import re
from datetime import date, datetime
from typing import Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.booknotification.com"

FAQ_QUESTION = re.compile(r'Are there upcoming new books by')
NO_BOOKS_ANSWER = 'does not have any upcoming books'
UPCOMING_HEADING = re.compile(r'Upcoming Books')

_DATE = r'([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})'
DATE_AFTER_TITLE = re.compile(rf'\s*will be released on\s+{_DATE}')
DATE_BEFORE_TITLE = re.compile(rf'coming out on\s+{_DATE}\s+called\s*$')


class BookNotificationScraper:
    """Scraper for Book Notification author pages."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def scrape_author_releases(self, author_config: Dict) -> List[Dict]:
        """
        Scrape the upcoming releases for one author.

        Args:
            author_config: An author entry from authors.yaml

        Returns:
            Book dictionaries for releases dated today or later

        Raises:
            requests.RequestException: if the author page cannot be fetched
            ValueError: if the config has no ID, or the page is not in a recognised format
        """
        author_id = author_config.get('book_notification_id')
        author_name = author_config.get('name')

        if not author_id:
            raise ValueError(f"No book_notification_id provided for {author_name}")

        author_url = f"{BASE_URL}/authors/{author_id}"
        soup = self.scrape_page(author_url)

        books = []
        for title, release_date in self.parse_upcoming_books(soup, author_url):
            if release_date >= date.today():
                logger.info(f"Found upcoming book: {title} - {release_date}")
                books.append(self.normalize_book_data(title, author_name, release_date, author_url))
        return books

    def scrape_page(self, url: str, timeout: int = 30) -> BeautifulSoup:
        """Fetch a page, raising requests.RequestException if it cannot be fetched."""
        logger.info(f"Scraping page: {url}")

        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()

        return BeautifulSoup(response.content, 'html.parser')

    def parse_upcoming_books(self, soup: BeautifulSoup, author_url: str) -> List[Tuple[str, date]]:
        """
        Extract (title, release date) for every upcoming book on an author page.

        Raises:
            ValueError: if the page does not positively say what is, or is not, upcoming.
                An empty list is only returned when the page says nothing is upcoming.
        """
        question = soup.find('h3', string=FAQ_QUESTION)
        if question is None:
            if soup.find('h5', string=UPCOMING_HEADING) is None:
                raise ValueError(f"Page not recognised, no 'Upcoming Books' section: {author_url}")
            return []

        answer = question.find_next('div', itemprop='text')
        if answer is None:
            raise ValueError(f"Upcoming-books FAQ has no answer: {author_url}")

        titles = answer.find_all('em')
        if not titles:
            if NO_BOOKS_ANSWER not in answer.get_text():
                raise ValueError(f"Upcoming-books FAQ answer could not be parsed: {author_url}")
            return []

        return [
            (' '.join(em.get_text().split()), self._release_date_for(em, author_url))
            for em in titles
        ]

    def _release_date_for(self, title_element, author_url: str) -> date:
        """Read the release date from the text next to a title's <em> element."""
        before = title_element.previous_sibling
        after = title_element.next_sibling

        match = (
            (isinstance(after, str) and DATE_AFTER_TITLE.match(after))
            or (isinstance(before, str) and DATE_BEFORE_TITLE.search(before))
        )
        if not match:
            raise ValueError(
                f"No release date found for '{title_element.get_text()}': {author_url}"
            )

        month, day, year = match.groups()
        return datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()

    def generate_book_id(self, title: str, author: str) -> str:
        """
        Generate the identifier for a book: the full author name and title, normalised.

        The release date is deliberately not part of it, so a date change keeps the same ID.
        """
        words = re.sub(r'[^\w\s]', '', f"{author} {title}".lower()).split()
        return '_'.join(words)

    def normalize_book_data(self, title: str, author: str, release_date: date, source_url: str) -> Dict:
        """Build the book dictionary stored in release_schedules.json."""
        return {
            'id': self.generate_book_id(title, author),
            'title': title,
            'author': author,
            'release_date': release_date,
            'source_url': source_url,
            'discovery_date': datetime.now().isoformat(),
            'last_checked': datetime.now().isoformat(),
            'notifications_sent': [],
        }
