# Class Availability Tracker

A cloud-hosted service that watches UTD Coursebook sections and notifies subscribed users when seats open via Discord DMs.

## Overview

Measurement of class availability is done by a background runner that scrapes the UTD Coursebook site using intelligent fallback scraping methods.
Users interact with the system via a Discord bot to track or untrack specific classes.

## Features

-   **Discord Integration**: Slash commands (`/track`, `/untrack`, `/list`) to manage subscriptions.
-   **Smart Notifications**: Background runner checks for changes every 15 minutes and DMs users immediately when a spot opens.
-   **Robust Scraping**: Multiple scraping methods with intelligent fallback (token extraction, curl_cffi TLS masquerading).
-   **CAPTCHA Bypass**: Token extraction method mimics real browser sessions to avoid detection.
-   **Health Monitoring**: Built-in health check endpoints for uptime monitoring.

## Quick Start

1.  Add the bot to your server or DM it.
2.  Use `/track CS 4349 006` to start watching a class.
3.  Receive a DM when the class opens!

## Deployment

### Prerequisites

- **Discord Bot Token**: Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
- **Supabase Project**: Set up at [Supabase](https://supabase.com) with tables created (see Database Setup)
- **Hosting Platform**: Railway (recommended) or Render (free tier)

### Environment Variables

Create a `.env` file or set these in your hosting platform:

```env
# Required
DISCORD_BOT_TOKEN=your_discord_bot_token_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key_here  # IMPORTANT: Use SERVICE ROLE KEY, not anon key

# Optional
PORT=8080  # Usually auto-set by hosting platform
LOG_ACCESS_KEY=debugme  # For /logs and /test-scrape endpoints
```

**Important**: The `SUPABASE_KEY` must be the **service role key** (not anon key) for Row Level Security policies to work. Get it from Supabase Dashboard → Settings → API → service_role key.

### Database Setup

Supabase tables should already be created. Ensure you have:

1. **subscriptions** table with columns: `label` (text), `user_id` (text), `timestamp` (timestamp)
2. **notified_state** table with columns: `label` (text), `last_notified` (timestamp), `last_status` (text), `enrolled` (integer)
3. Row Level Security (RLS) enabled with service role policies

If needed, run these SQL commands in Supabase SQL Editor:

```sql
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE notified_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service Role Full Access" ON subscriptions
AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service Role Full Access" ON notified_state
AS PERMISSIVE FOR ALL TO service_role USING (true) WITH CHECK (true);
```

### Deploy to Railway (Recommended)

1. **Connect Repository**:
   - Go to [Railway](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select this repository

2. **Configure Environment Variables**:
   - Go to project settings → Variables
   - Add all required environment variables (see above)

3. **Deploy**:
   - Railway will automatically detect the Dockerfile and deploy
   - The bot will start automatically
   - Copy the service URL (for Uptime Robot)

4. **Set Up Uptime Robot** (Keep service alive):
   - Go to [Uptime Robot](https://uptimerobot.com)
   - Add new monitor
   - Type: HTTP(s)
   - URL: `https://your-app.railway.app/healthz` (or just `/`)
   - Interval: 5 minutes
   - This keeps the service alive on free tier

**Railway Free Tier**: $5 credit/month, usually sufficient for Discord bot + checking loop.

### Deploy to Render (Alternative)

1. **Create Web Service**:
   - Go to [Render](https://render.com)
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure**:
   - **Build Command**: (leave empty, Dockerfile handles it)
   - **Start Command**: `python -u -m src.bot`
   - **Environment**: Python 3
   - Add all required environment variables

3. **Set Up Health Check**:
   - Health Check Path: `/healthz` or `/`
   - Render will monitor this endpoint

4. **Set Up Uptime Robot** (if on free tier):
   - Same as Railway instructions above
   - URL: `https://your-app.onrender.com/healthz`

**Render Free Tier**: Services spin down after 15 minutes of inactivity. Use Uptime Robot to keep it alive.

## Debugging & Monitoring

### Health Check Endpoints

- `/` or `/healthz`: Basic health check (returns 200 if bot is running)
- `/status`: Detailed status JSON (bot status, database connection, scraper availability)
- `/logs?key=YOUR_LOG_ACCESS_KEY`: View recent logs (protected)
- `/test-scrape?query=CS 4349&key=YOUR_LOG_ACCESS_KEY`: Manually test scraping (protected)
- `/robots.txt`: Returns robots.txt for crawlers

### Example Status Response

```json
{
  "bot_status": "online",
  "database_connected": true,
  "check_loop_running": true,
  "available_scrapers": ["token_extraction", "curl_cffi_tls"],
  "subscription_count": 3,
  "total_tracked_courses": 2,
  "health": "ok"
}
```

### Viewing Logs

1. Set `LOG_ACCESS_KEY` environment variable (or use default "debugme")
2. Visit: `https://your-app.railway.app/logs?key=YOUR_LOG_ACCESS_KEY`
3. Or test scraping: `https://your-app.railway.app/test-scrape?query=CS 4349&key=YOUR_LOG_ACCESS_KEY`

## How It Works

### Scraping Methods (Fallback Chain)

1. **Token Extraction** (Primary - Most Reliable):
   - Extracts CSRF token from UTD Coursebook homepage
   - POSTs to AJAX endpoint with proper headers
   - Mimics real browser session (lowest CAPTCHA detection)
   - Lightweight (~10-20MB memory)

2. **curl_cffi TLS Masquerading** (Fallback):
   - Uses curl_cffi to bypass TLS fingerprinting
   - Direct URL scraping with Chrome 120 impersonation
   - Only used if token extraction fails

3. **Direct URL** (Last Resort):
   - Simple GET request to coursebook URL
   - Fallback if other methods fail

### Background Loop

- Runs every 15 minutes automatically
- Checks all subscribed courses
- Compares current state with previous state
- Sends DM notification if:
  - Status changed (e.g., "Closed" → "Open")
  - Seats opened (enrolled decreased)
  - Last notification was >1 hour ago (prevents spam)

## Troubleshooting

### Build Fails on Render/Railway

**Issue**: `curl_cffi` installation fails (requires Rust).

**Solution**: This is okay! The app will work without curl_cffi. Token extraction method is primary and doesn't require it. Check logs to confirm token extraction is working.

### CAPTCHA/Bot Detection

**Issue**: Scraping returns empty results or CAPTCHA page.

**Solution**:
- Check logs via `/logs` endpoint to see which method is being used
- Token extraction method should bypass most detection
- If still blocked, check UTD Coursebook for changes in their API
- Try `/test-scrape` endpoint to debug

### Bot Not Responding to Commands

**Issue**: Discord commands don't work.

**Solutions**:
- Check `/status` endpoint - `bot_status` should be "online"
- Verify `DISCORD_BOT_TOKEN` is correct
- Check bot has necessary permissions in your Discord server
- Ensure bot is in the server/guild where commands are used

### Database Connection Issues

**Issue**: `database_connected: false` in `/status`.

**Solutions**:
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- **Important**: `SUPABASE_KEY` must be **service role key** (not anon key)
- Check Supabase project is active
- Verify RLS policies allow service role access

### Notifications Not Sending

**Issue**: Classes open but no DMs sent.

**Solutions**:
- Check background loop is running: `/status` → `check_loop_running: true`
- Verify users haven't blocked the bot (can't send DMs to blocked users)
- Check logs for errors in `notify_users` function
- Verify backoff logic isn't preventing notifications (waits 1 hour between notifications for same course)

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # (if .env.example exists, otherwise create manually)
# Edit .env with your credentials

# Run the bot
python -m src.bot

# Test scraping directly
python -m src.checker_http CS 4349
python -m src.scraper CS 4349 001
```

## Project Structure

```
├── src/
│   ├── bot.py              # Main Discord bot + health server
│   ├── scraper.py          # Scraper orchestrator (fallback chain)
│   ├── checker_http.py     # Token extraction scraper (primary)
│   ├── checker_tls.py      # curl_cffi TLS scraper (fallback)
│   ├── checker_playwright.py  # Playwright scraper (optional)
│   ├── parser.py           # HTML parser for coursebook results
│   ├── database.py         # Supabase database client
│   └── runner.py           # Standalone runner (for GitHub Actions)
├── Dockerfile              # Docker configuration
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Contributing

Feel free to open issues or pull requests for improvements!

## License

MIT
