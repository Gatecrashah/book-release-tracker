# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

```bash
# Install dependencies
uv sync

# Run local testing with environment variables
source .env && uv run python book_monitor.py

# Test specific author scraper
uv run python test_scraper.py

# Test email functionality
source .env && uv run python email_sender.py
```

## Architecture Overview

This is an automated book release tracker that monitors favorite authors and sends email notifications via GitHub Actions.

### Core Components

- **BookMonitor** (`book_monitor.py`): Main orchestrator that coordinates scraping, change detection, and notifications
- **BaseBookScraper** (`scrapers/base_book_scraper.py`): Abstract base class defining scraper interface with common HTTP handling and data normalization
- **BookNotificationScraper** (`scrapers/book_notification.py`): Primary scraper that extracts book release data from BookNotification.com FAQ sections using regex patterns
- **EmailSender** (`email_sender.py`): Handles all email notifications via Resend API with HTML templates

### Data Flow

1. **Configuration**: Authors defined in `authors.yaml` with Book Notification IDs
2. **Scraping**: FAQ-based extraction using regex pattern `"has a new book coming out on DATE called TITLE"`
3. **Storage**: Book release data persisted in `release_schedules.json` (auto-managed by GitHub Actions)
4. **Notifications**: New discoveries, 7-day reminders, and release day alerts sent via email
5. **Cleanup**: Automatic removal of releases older than 6 months

### Scraping Strategy

The scraper targets FAQ sections on Book Notification author pages that contain the pattern "Author has a new book coming out on DATE called TITLE". This approach provides more reliable data than table parsing and directly answers the core question about upcoming releases.

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
2. Use `test_scraper.py` for iterative scraper development and validation
3. Test email functionality before deploying changes
4. Never commit sensitive data - `.env` is gitignored

### Data Management

- `release_schedules.json` should be reset to empty `{"books": [], "last_updated": "..."}` when scraper logic changes significantly
- The system automatically handles deduplication and tracks notification history
- Book IDs are generated from normalized titles and authors to prevent duplicates