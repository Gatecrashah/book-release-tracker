"""Behaviour tests for the monitoring cycle, with the scraper and email sender faked."""

import json
import os
from datetime import date, datetime, timedelta

import pytest
import yaml

from book_monitor import BookMonitor

AUTHOR = "Lee Child"
URL = "https://example.test/authors/lee-child"
RELEASE = date(2027, 3, 23)


class FakeMail:
    def __init__(self):
        self.sent = []
        self.failing = False

    def _send(self, kind, payload):
        if self.failing:
            raise RuntimeError("Resend rejected email (status 401)")
        self.sent.append((kind, payload))

    def send_book_discovery_alert(self, books):
        self._send("discovery", [b["title"] for b in books])

    def send_date_change_alert(self, books):
        self._send("date_change", [(b["title"], b["previous_release_date"], str(b["release_date"])) for b in books])

    def send_release_reminder(self, books):
        self._send("reminder", [b["title"] for b in books])

    def send_release_day_alert(self, books):
        self._send("release", [b["title"] for b in books])

    def send_tracker_failure_alert(self, error_details):
        self.sent.append(("failure", error_details))


@pytest.fixture
def monitor(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("EMAIL_TO", "reader@example.test")

    m = BookMonitor()
    m.email_sender = FakeMail()
    m.schedules_file = str(tmp_path / "release_schedules.json")
    m.authors_file = str(tmp_path / "authors.yaml")
    authors = [{"name": AUTHOR, "book_notification_id": "lee-child", "status": "active"}]
    (tmp_path / "authors.yaml").write_text(yaml.safe_dump({"authors": authors}))
    listed(m, [])
    return m


def listed(m, releases):
    """Make the fake source list these (title, release date) pairs for the author."""
    m.scraper.scrape_author_releases = lambda author: [
        m.scraper.normalize_book_data(title, AUTHOR, release, URL) for title, release in releases
    ]


def saved(m):
    with open(m.schedules_file, encoding="utf-8") as f:
        return json.load(f)["books"]


def stored_book(release=RELEASE, last_seen=None, notifications=()):
    """A book as it sits in the schedules file: last seen on a date, with (type, date) notifications sent."""
    return {
        "id": "lee_child_zero_margin",
        "title": "Zero Margin",
        "author": AUTHOR,
        "release_date": release.isoformat(),
        "last_checked": datetime.combine(last_seen or release, datetime.min.time()).isoformat(),
        "notifications_sent": [
            {"type": kind, "date": datetime.combine(sent, datetime.min.time()).isoformat()}
            for kind, sent in notifications
        ],
    }


def due_offsets(should_send, book, days=range(-10, 7)):
    """Days relative to release on which an alert is due, for a book the source keeps listing until release."""
    release = date.fromisoformat(book["release_date"])
    due = []
    for offset in days:
        today = release + timedelta(days=offset)
        seen = dict(book, last_checked=min(today, release).isoformat())
        if should_send(seen, today):
            due.append(offset)
    return due


# --- the monitoring cycle ---------------------------------------------------


def test_new_book_is_announced_once(monitor):
    listed(monitor, [("Zero Margin", RELEASE)])

    assert monitor.run_monitoring_cycle() is True
    assert monitor.run_monitoring_cycle() is True

    assert monitor.email_sender.sent == [("discovery", ["Zero Margin"])]
    [book] = saved(monitor)
    assert book["release_date"] == "2027-03-23"
    assert [n["type"] for n in book["notifications_sent"]] == ["discovery"]


def test_failed_email_fails_the_run_and_is_retried_next_run(monitor):
    listed(monitor, [("Zero Margin", RELEASE)])
    monitor.email_sender.failing = True

    assert monitor.run_monitoring_cycle() is False
    assert not os.path.exists(monitor.schedules_file)

    monitor.email_sender.failing = False
    assert monitor.run_monitoring_cycle() is True
    assert ("discovery", ["Zero Margin"]) in monitor.email_sender.sent


def test_scrape_failure_fails_the_run_but_keeps_known_books(monitor):
    listed(monitor, [("Zero Margin", RELEASE)])
    monitor.run_monitoring_cycle()

    def broken(author):
        raise ValueError("Page not recognised")

    monitor.scraper.scrape_author_releases = broken
    monitor.email_sender.sent.clear()

    assert monitor.run_monitoring_cycle() is False
    [(kind, details)] = monitor.email_sender.sent
    assert kind == "failure" and AUTHOR in details and "Page not recognised" in details
    assert [b["title"] for b in saved(monitor)] == ["Zero Margin"]


def test_corrupt_schedules_file_fails_the_run_and_is_left_alone(monitor):
    with open(monitor.schedules_file, "w") as f:
        f.write("{not json")
    listed(monitor, [("Zero Margin", RELEASE)])

    assert monitor.run_monitoring_cycle() is False
    assert open(monitor.schedules_file).read() == "{not json"
    assert [kind for kind, _ in monitor.email_sender.sent] == ["failure"]


def test_book_stored_under_the_old_id_scheme_is_recognised(monitor):
    old = dict(stored_book(notifications=[("discovery", date(2026, 7, 28))]), id="lee_child_zero_margin_2027")
    with open(monitor.schedules_file, "w") as f:
        json.dump({"books": [old]}, f)
    listed(monitor, [("Zero Margin", RELEASE)])

    assert monitor.run_monitoring_cycle() is True
    assert monitor.email_sender.sent == []
    assert [b["id"] for b in saved(monitor)] == ["lee_child_zero_margin"]


def test_date_change_across_a_year_boundary_updates_the_same_book(monitor):
    listed(monitor, [("Zero Margin", date(2026, 12, 15))])
    monitor.run_monitoring_cycle()
    listed(monitor, [("Zero Margin", date(2027, 2, 1))])
    monitor.run_monitoring_cycle()

    assert monitor.email_sender.sent == [
        ("discovery", ["Zero Margin"]),
        ("date_change", [("Zero Margin", "2026-12-15", "2027-02-01")]),
    ]
    [book] = saved(monitor)
    assert book["release_date"] == "2027-02-01"
    assert [n["type"] for n in book["notifications_sent"]] == ["discovery", "date_change"]
    assert book["notifications_sent"][1]["old_date"] == "2026-12-15"


def test_book_listed_twice_in_one_scrape_is_stored_and_announced_once(monitor):
    listed(monitor, [("Zero Margin", RELEASE), ("Zero Margin", RELEASE)])
    monitor.run_monitoring_cycle()

    assert len(saved(monitor)) == 1
    assert monitor.email_sender.sent == [("discovery", ["Zero Margin"])]


def test_similar_titles_stay_separate_books(monitor):
    listed(monitor, [("The Way of Kings", RELEASE), ("The Way of Shadows", RELEASE)])
    monitor.run_monitoring_cycle()

    assert sorted(b["title"] for b in saved(monitor)) == ["The Way of Kings", "The Way of Shadows"]


def test_book_no_longer_listed_keeps_its_last_seen_date(monitor):
    listed(monitor, [("Zero Margin", RELEASE)])
    monitor.run_monitoring_cycle()
    first_seen = saved(monitor)[0]["last_checked"]

    listed(monitor, [])
    monitor.run_monitoring_cycle()

    assert saved(monitor)[0]["last_checked"] == first_seen


# --- when alerts are due ----------------------------------------------------

DISCOVERED_EARLY = ("discovery", RELEASE - timedelta(days=200))


def test_reminder_is_due_any_day_in_the_week_before_release(monitor):
    book = stored_book(notifications=[DISCOVERED_EARLY])
    assert due_offsets(monitor.should_send_reminder, book) == [-7, -6, -5, -4, -3, -2, -1]


@pytest.mark.parametrize(
    "already_sent",
    [
        ("reminder", RELEASE - timedelta(days=7)),
        ("reminder", RELEASE - timedelta(days=5)),
        ("discovery", RELEASE - timedelta(days=4)),
        ("date_change", RELEASE - timedelta(days=6)),
    ],
    ids=["reminded-on-time", "reminded-late", "discovered-that-week", "date-changed-that-week"],
)
def test_no_reminder_when_an_email_about_the_book_went_out_that_week(monitor, already_sent):
    book = stored_book(notifications=[DISCOVERED_EARLY, already_sent])
    assert due_offsets(monitor.should_send_reminder, book) == []


def test_reminder_is_sent_again_after_the_date_moves_to_a_later_week(monitor):
    reminded_for_old_date = ("reminder", RELEASE - timedelta(days=37))
    book = stored_book(notifications=[DISCOVERED_EARLY, reminded_for_old_date])
    assert due_offsets(monitor.should_send_reminder, book) == [-7, -6, -5, -4, -3, -2, -1]


def test_release_alert_is_due_from_release_day_for_three_more_days(monitor):
    book = stored_book(notifications=[DISCOVERED_EARLY])
    assert due_offsets(monitor.should_send_release_day_alert, book) == [0, 1, 2, 3]


def test_release_alert_is_sent_only_once(monitor):
    book = stored_book(notifications=[DISCOVERED_EARLY, ("release_day", RELEASE + timedelta(days=1))])
    assert due_offsets(monitor.should_send_release_day_alert, book) == []


def test_no_alerts_for_a_book_the_source_stopped_listing(monitor):
    withdrawn = stored_book(last_seen=RELEASE - timedelta(days=40), notifications=[DISCOVERED_EARLY])
    for offset in range(-10, 7):
        today = RELEASE + timedelta(days=offset)
        assert not monitor.should_send_reminder(withdrawn, today)
        assert not monitor.should_send_release_day_alert(withdrawn, today)


def test_release_alert_still_fires_if_the_source_drops_the_book_on_release_day(monitor):
    dropped_the_day_before = stored_book(last_seen=RELEASE - timedelta(days=1), notifications=[DISCOVERED_EARLY])
    for offset in (0, 1, 2, 3):
        assert monitor.should_send_release_day_alert(dropped_the_day_before, RELEASE + timedelta(days=offset))
