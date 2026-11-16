# Book Release Tracker

Automated book release tracker that monitors your favorite authors for new book releases and sends email notifications via Resend API.

## 🎯 Features

- **Automated Daily Monitoring**: Checks for new releases every day at 9:00 AM UTC
- **Smart Notifications**:
  - New book discoveries
  - Release date changes
  - A reminder in the week before release
  - An alert when the book is out
- **Catches Up**: A skipped or failed run does not lose a reminder or release alert; the next run sends it
- **Fails Loudly**: An unreachable or unrecognised author page, a failed email or a corrupt data file fails the run
- **Multi-Author Support**: Track multiple authors simultaneously
- **Centralized Data Source**: Uses Book Notification for reliable release data
- **Email Integration**: Beautiful HTML emails via Resend API
- **Data Retention**: Automatic cleanup of releases older than 6 months

## 📚 Currently Tracked Authors

- Brandon Sanderson
- Stephen Hunter
- James S. A. Corey
- Jack Carr
- Lee Child
- Jeffrey Archer
- David Baldacci
- Michael Connelly

## 🏗️ Architecture

```
book-release-tracker/
├── scrapers/
│   ├── book_notification.py      # Scraper for BookNotification.com author pages
│   └── __init__.py
├── tests/
│   ├── fixtures/                 # Trimmed copies of real author pages
│   ├── test_scraper_parsing.py   # Parser tests against the fixtures
│   └── test_monitor.py           # Monitoring cycle and alert timing
├── book_monitor.py               # Main orchestration
├── email_sender.py               # Resend API email notifications
├── email_templates.py            # HTML email templates
├── authors.yaml                  # Author tracking configuration
├── release_schedules.json        # Book release data (auto-managed)
└── .github/workflows/
    └── book_monitor.yml          # Daily GitHub Actions workflow
```

## ⚙️ Setup

### Prerequisites
- Python 3.11+
- UV package manager
- Resend API key
- GitHub repository with Actions enabled

### Environment Variables
Set up GitHub Secrets:
```
RESEND_API_KEY=your-resend-api-key
EMAIL_TO=your-email@example.com
```

### Installation
```bash
# Clone repository
git clone https://github.com/Gatecrashah/book-release-tracker.git
cd book-release-tracker

# Install dependencies
uv sync

# Test configuration (with environment variables set)
source .env && uv run python email_sender.py
```

## 📧 Email Notifications

### Notification Types
1. **New Discovery** (also sent when a release date changes): "📚 1 new book discovered!"
2. **Release Reminder**: "📅 1 book releasing within a week!"
3. **Available Now**: "🎉 1 book available now!"

A reminder is sent once in the week before release, and skipped if another email about the
book already went out that week. A release alert is sent once, on release day or up to three
days after. Books the source stopped listing more than three days ago get neither.

### Sample Email
```html
New Discovery
1 new book from your favorite authors

NEW DISCOVERY
Tailored Realities
by Brandon Sanderson
Release Date: December 09, 2025
```

## 🤖 Automation

### GitHub Actions Workflow
- **Schedule**: Daily at 9:00 AM UTC
- **Triggers**: Manual trigger + code changes
- **Actions**: 
  1. Scrape author pages for new releases
  2. Detect changes and new discoveries
  3. Send email notifications
  4. Update release schedules
  5. Commit changes to repository

### Data Management
- `release_schedules.json` - Automatically managed by GitHub Actions
- `authors.yaml` - Manual configuration (add new authors here)
- Automatic cleanup of releases older than 6 months

## 📊 Adding New Authors

Edit `authors.yaml`:
```yaml
authors:
  - name: "New Author Name"
    book_notification_id: "author-url-slug"
    status: "active"
```

To find the `book_notification_id`:
1. Go to https://www.booknotification.com/
2. Search for your author
3. The URL slug is the ID (e.g., "brandon-sanderson")

## 🛠️ Local Testing

```bash
# Run the test suite (no network, no emails)
uv run pytest

# Test email configuration
source .env && uv run python email_sender.py

# Test scraper for specific author
uv run python -c "
from scrapers import BookNotificationScraper
scraper = BookNotificationScraper()
books = scraper.scrape_author_releases({'name': 'Brandon Sanderson', 'book_notification_id': 'brandon-sanderson'})
print(f'Found {len(books)} books')
"

# Run full monitoring cycle
source .env && uv run python book_monitor.py
```

## 📈 Monitoring & Logs

- GitHub Actions logs available in repository
- Local logs saved to `book_monitor.log`
- Email delivery tracking via Resend dashboard
- A failed run exits non-zero, so GitHub marks it red, and a failure alert email is attempted

## 🔧 Troubleshooting

### Common Issues

**"No books found"**
```bash
# Verify author configuration
uv run python -c "import yaml; print(yaml.safe_load(open('authors.yaml')))"
```

**"Email not sending"**
```bash
# Test email configuration
source .env && uv run python email_sender.py
```

**"Scraper failing"**
- Check GitHub Actions logs
- Verify Book Notification site accessibility
- If the page format changed, refresh `tests/fixtures/` from the live page and update the parser

### Debug Mode
```bash
# Enable debug logging
source .env && uv run python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from book_monitor import BookMonitor
monitor = BookMonitor()
monitor.run_monitoring_cycle()
"
```

## 📄 License

This project is for personal use. Feel free to fork and adapt for your own book tracking needs.

---

**🤖 Automated by GitHub Actions | 📧 Powered by Resend API | 🏗️ Built with Python**