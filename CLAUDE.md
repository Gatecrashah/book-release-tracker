# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

```bash
# Install dependencies
uv sync

# Run the tests (offline: saved pages, faked email)
uv run pytest

# Run local testing with environment variables
source .env && uv run python book_monitor.py

# Scrape a few authors live and print what was found
uv run python test_scraper.py

# Test email functionality
source .env && uv run python email_sender.py
```

## Architecture Overview

This is an automated book release tracker that monitors favorite authors and sends email notifications via GitHub Actions.

### Core Components

- **BookMonitor** (`book_monitor.py`): Main orchestrator that coordinates scraping, change detection, and notifications
- **BookNotificationScraper** (`scrapers/book_notification.py`): Fetches BookNotification.com author pages and extracts upcoming releases from the "Are there upcoming new books by ..." FAQ answer
- **EmailSender** (`email_sender.py`): Handles all email notifications via Resend API with HTML templates

### Data Flow

1. **Configuration**: Authors defined in `authors.yaml` with Book Notification IDs
2. **Scraping**: Each `<em>` in the FAQ answer is a title; the date is in the text next to it
3. **Storage**: Book release data persisted in `release_schedules.json` (auto-managed by GitHub Actions)
4. **Notifications**: New discoveries, date changes, a reminder in the week before release, and a release alert
5. **Cleanup**: Automatic removal of releases older than 6 months

### Scraping Strategy

The FAQ answer has three forms, all covered by fixtures in `tests/fixtures/`:

- one book: `Author has a new book coming out on DATE called <em>TITLE</em>.`
- several: `Author has N new books coming out: <em>TITLE</em> will be released on DATE. ...`
- none: `Author does not have any upcoming books with a set publication date ...`

Some author pages have no such FAQ entry, which also means nothing is upcoming.

The scraper raises when a page fits none of these, rather than returning an empty list: "no upcoming books" must be something the page says, never the result of a failed parse. When the site changes, save the new page into `tests/fixtures/` (trimmed to headings and FAQ blocks) and update the parser against it.

### Failure Handling

- A scrape failure for one author does not stop the others; the run saves state, then fails.
- A failed email fails the run without saving state, so the next run retries it.
- `last_checked` is only updated when a book appears in a scrape. Books not seen for more than 3 days get no reminder or release alert (they were withdrawn or renamed at the source).
- Reminders and release alerts are due inside a window, not on one exact day, so a missed run is caught up.

## Key Implementation Details

### Environment Variables
Required for local testing and production:
- `RESEND_API_KEY`: For email notifications
- `EMAIL_TO`: Recipient email address

### GitHub Actions Integration
- Daily schedule (9:00 AM UTC)
- Automatically commits changes to `release_schedules.json`
- Uses GitHub Secrets for API keys

### Author Configuration
Add new authors to `authors.yaml`:
```yaml
authors:
  - name: "Author Name"
    book_notification_id: "author-url-slug"  # From booknotification.com URL
    status: "active"
```

### Local Development Workflow

1. Create `.env` file with required environment variables (see `.env.example`)
2. Change the parser against the fixtures with `uv run pytest`; use `test_scraper.py` to compare with the live site
3. Test email functionality before deploying changes
4. Never commit sensitive data - `.env` is gitignored

### Data Management

- The system automatically handles deduplication and tracks notification history
- Book IDs are the normalised author name and full title, and are recomputed when the file is loaded. The release date is not part of the ID, so a date change keeps the same book.

### Important: release_schedules.json Handling

**NEVER manually commit `release_schedules.json`** - it's auto-managed by GitHub Actions.

When committing other changes, always restore this file first to avoid conflicts:

```bash
# Before pushing any commits:
git restore release_schedules.json
git pull --rebase
git push
```

Why: GitHub Actions runs daily and auto-commits updates to this file. If you include it in your commits, you'll get merge conflicts on every push.