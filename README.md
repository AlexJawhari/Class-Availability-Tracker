# Class Availability Tracker

A Discord bot that monitors UTD Coursebook for class availability and sends instant notifications when seats open up.

## Overview

This bot helps students track course availability by automatically checking the UTD Coursebook every 15 minutes. When a tracked class section opens or changes status, subscribers receive an immediate Discord DM notification.

## Features

- **Discord Slash Commands**: Simple commands (`/track`, `/untrack`, `/list`) to manage your course subscriptions
- **Real-time Notifications**: Instant DM alerts when classes open or status changes
- **Intelligent Scraping**: Multiple fallback methods ensure reliable data collection even when facing CAPTCHA protection
- **Smart Rate Limiting**: Prevents notification spam with intelligent backoff logic
- **Health Monitoring**: Built-in status endpoints for monitoring bot health and performance

## Usage

### Commands

- `/track <course>` - Start tracking a course section (e.g., `/track CS 4349 006`)
- `/untrack <course>` - Stop tracking a course section
- `/list` - View all courses you're currently tracking

### How It Works

1. Add the bot to your Discord server or DM it directly
2. Use `/track` to subscribe to courses you want to monitor
3. The bot checks availability every 15 minutes in the background
4. When a spot opens, you'll receive a DM with the course status and enrollment information

## Technical Details

### Architecture

The bot uses a multi-layered scraping approach with automatic fallback:

1. **Token Extraction Method** (Primary): Extracts CSRF tokens from the Coursebook homepage and makes authenticated requests. This lightweight method mimics real browser sessions to avoid detection.

2. **TLS Masquerading** (Fallback): Uses curl_cffi to bypass TLS fingerprinting if the primary method fails.

3. **Direct Scraping** (Last Resort): Simple HTTP requests as a final fallback.

The bot runs a background task loop that checks all subscribed courses every 15 minutes, compares the current state with the previous state, and sends notifications when:
- Course status changes (e.g., "Closed" → "Open")
- Enrollment decreases (seats become available)
- At least 1 hour has passed since the last notification (prevents spam)

### Tech Stack

- **Python 3.11+** - Core language
- **Discord.py** - Discord bot framework
- **Supabase** - Database for storing subscriptions and state
- **BeautifulSoup4** - HTML parsing
- **Docker** - Containerization for deployment

### Health Endpoints

The bot exposes several HTTP endpoints for monitoring:

- `GET /` or `/healthz` - Basic health check
- `GET /status` - Detailed status JSON with bot state, database connection, and scraper availability
- `GET /logs?key=<key>` - View recent application logs (protected)
- `GET /test-scrape?query=<course>&key=<key>` - Manually test scraping functionality (protected)

## Development

### Prerequisites

- Python 3.11 or higher
- Discord Bot Token
- Supabase project with appropriate database tables

### Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see `.env.example` if available)
4. Run the bot: `python -m src.bot`

### Project Structure

```
├── src/
│   ├── bot.py              # Main Discord bot + health server
│   ├── scraper.py          # Scraper orchestrator (fallback chain)
│   ├── checker_http.py     # Token extraction scraper (primary)
│   ├── checker_tls.py      # curl_cffi TLS scraper (fallback)
│   ├── parser.py           # HTML parser for coursebook results
│   ├── database.py         # Supabase database client
│   └── runner.py           # Standalone runner utilities
├── Dockerfile              # Docker configuration
├── requirements.txt        # Python dependencies
└── README.md
```

## Deployment

The bot is designed to run on containerized hosting platforms like Render or Railway. The Dockerfile handles all dependencies and configuration. For free-tier hosting, services may spin down after inactivity, so consider using a monitoring service like Uptime Robot to keep the service alive.

## License

MIT
