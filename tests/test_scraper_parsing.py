"""Parser tests against trimmed copies of real booknotification.com author pages."""

from datetime import date
from pathlib import Path

import pytest
import requests
from bs4 import BeautifulSoup

from scrapers import BookNotificationScraper

FIXTURES = Path(__file__).parent / "fixtures"
URL = "https://example.test/authors/x"


def parse(html: str):
    return BookNotificationScraper().parse_upcoming_books(BeautifulSoup(html, "html.parser"), URL)


def parse_fixture(name: str):
    return parse((FIXTURES / f"{name}.html").read_text(encoding="utf-8"))


def faq(answer: str) -> str:
    return (
        "<h5>Upcoming Books</h5>"
        '<div class="faq"><h3 itemprop="name">Are there upcoming new books by A B?</h3>'
        f'<div class="faqanswer"><div itemprop="text">{answer}</div></div></div>'
    )


def test_single_upcoming_book():
    assert parse_fixture("lee-child") == [("Zero Margin", date(2027, 3, 23))]


def test_several_upcoming_books():
    assert parse_fixture("nora-roberts") == [
        ("Birth of the Witch", date(2026, 11, 17)),
        ("Perfect in Death", date(2027, 2, 2)),
        ("The Missing", date(2027, 5, 25)),
    ]


def test_many_upcoming_books_including_last_one_without_trailing_period():
    books = parse_fixture("james-patterson")
    assert len(books) == 11
    assert books[0] == ("The Murder Trial", date(2026, 11, 23))
    assert books[6] == ("27 Stars", date(2027, 4, 19))
    assert books[-1] == ("The Protector", date(2027, 10, 4))


def test_faq_says_nothing_upcoming():
    assert parse_fixture("stephen-hunter") == []


def test_author_page_without_upcoming_faq():
    assert parse_fixture("jeffrey-archer") == []


@pytest.mark.parametrize(
    "title",
    ["Mr. Mercedes", "It", "And Then There Were None", "Dr. No", "Vol. 2: What Is Called Home?"],
)
def test_awkward_titles_survive_in_both_formats(title):
    single = faq(f"A B has a new book coming out on May 1st, 2027 called <em>{title}</em>.")
    several = faq(
        f"A B has two new books coming out: <em>{title}</em> will be released on May 1st, 2027. "
        "<em>Other</em> will be released on June 2nd, 2027"
    )
    assert parse(single) == [(title, date(2027, 5, 1))]
    assert parse(several) == [(title, date(2027, 5, 1)), ("Other", date(2027, 6, 2))]


@pytest.mark.parametrize(
    "html",
    [
        "<h1>Verify you are human</h1>",
        faq("A B's next novel, Foo, arrives in May 2027."),
        faq("A B has a new book coming out in Fall 2027 called <em>Foo</em>."),
        faq("A B has a new book coming out on Smarch 1st, 2027 called <em>Foo</em>."),
        '<h5>Upcoming Books</h5><h3 itemprop="name">Are there upcoming new books by A B?</h3>',
    ],
    ids=["block-page", "reworded-answer", "vague-date", "invalid-month", "question-without-answer"],
)
def test_unrecognised_pages_raise_instead_of_looking_empty(html):
    with pytest.raises(ValueError):
        parse(html)


def test_book_id_is_full_author_and_title_without_the_date():
    scraper = BookNotificationScraper()
    assert scraper.generate_book_id("The Way of Kings", "A B") != scraper.generate_book_id("The Way of Shadows", "A B")
    assert scraper.generate_book_id("Mr. Mercedes!", "James S. A. Corey") == "james_s_a_corey_mr_mercedes"


def fetch_landing_on(final_url: str, monkeypatch):
    """Fetch an author page whose HTTP redirects end at final_url, serving a real author page there."""
    response = requests.Response()
    response.status_code = 200
    response.url = final_url
    response._content = (FIXTURES / "lee-child.html").read_bytes()
    scraper = BookNotificationScraper()
    monkeypatch.setattr(scraper.session, "get", lambda url, timeout: response)
    return scraper.scrape_page("https://www.booknotification.com/authors/lee-child")


def test_redirect_away_from_author_page_raises(monkeypatch):
    with pytest.raises(ValueError):
        fetch_landing_on("https://www.booknotification.com/browser-update.html", monkeypatch)

    soup = fetch_landing_on("https://www.booknotification.com/authors/lee-child/", monkeypatch)
    assert "Are there upcoming new books by Lee Child?" in [h3.get_text() for h3 in soup.find_all("h3")]
