"""Tests for what the notification emails say."""

from datetime import date

import pytest

import email_sender
from email_sender import EmailSender
from email_templates import EmailTemplates

BOOK = {
    "title": "Zero <Margin> & Co",
    "author": "Lee Child",
    "release_date": "2027-03-05",
    "source_url": "https://example.test/authors/lee-child",
}


@pytest.mark.parametrize("notification_type", sorted(EmailTemplates.NOTIFICATION_CONFIGS))
def test_every_notification_type_renders_the_book_with_escaped_title(notification_type):
    html = EmailTemplates.create_book_notification_email([BOOK], notification_type)

    assert "Zero &lt;Margin&gt; &amp; Co" in html
    assert "by Lee Child" in html
    assert "March 5, 2027" in html
    assert EmailTemplates.NOTIFICATION_CONFIGS[notification_type]["badge_text"] in html


def test_date_change_email_shows_the_previous_date():
    changed = dict(BOOK, release_date=date(2027, 10, 5), previous_release_date="2027-10-01")
    html = EmailTemplates.create_book_notification_email([changed], "date_change")

    assert "October 5, 2027" in html
    assert "Previously" in html and "October 1, 2027" in html


def test_other_emails_do_not_mention_a_previous_date():
    assert "Previously" not in EmailTemplates.create_book_notification_email([BOOK], "discovery")


class Response:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = '{"message": "API key is invalid"}'

    def json(self):
        return {"id": "email-1"}


@pytest.fixture
def sender(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("EMAIL_TO", "reader@example.test")
    return EmailSender()


def test_send_posts_subject_and_recipient_with_a_timeout(sender, monkeypatch):
    calls = []
    monkeypatch.setattr(email_sender.requests, "post", lambda url, **kw: calls.append(kw) or Response(200))

    sender.send_date_change_alert([dict(BOOK, previous_release_date="2027-03-01")])

    [call] = calls
    assert call["json"]["to"] == ["reader@example.test"]
    assert call["json"]["subject"] == "🗓️ Release date changed for 1 book"
    assert call["timeout"] > 0


def test_rejected_email_raises_with_the_api_response(sender, monkeypatch):
    monkeypatch.setattr(email_sender.requests, "post", lambda url, **kw: Response(403))

    with pytest.raises(RuntimeError, match="403.*API key is invalid"):
        sender.send_release_reminder([BOOK])
