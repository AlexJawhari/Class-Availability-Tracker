# src/bot.py
import os
import sys
import threading
import time
import io
import collections
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# --- AUTONOMOUS LOGGING INFRASTRUCTURE ---
# Capture the last N lines of logs in memory to expose via web endpoint.
LOG_BUFFER_SIZE = 2000
log_buffer = collections.deque(maxlen=LOG_BUFFER_SIZE)

class LogCapture(io.StringIO):
    def __init__(self, original_stream):
        super().__init__()
        self.original_stream = original_stream

    def write(self, s):
        # Write to original stream (so it shows in Render console)
        self.original_stream.write(s)
        self.original_stream.flush() # Ensure immediate output
        
        # Write to memory buffer
        # Splitlines to handle chunks properly? 
        # Simpler: just append raw string, or handle line splitting on read.
        # Let's simple append each write as a "line" if it contains newline?
        # A simple deque of strings is easiest.
        if s:
            log_buffer.append(s)

    def flush(self):
        self.original_stream.flush()

# Redirect stdout/stderr
sys.stdout = LogCapture(sys.stdout)
sys.stderr = LogCapture(sys.stderr)

print(">>> BOT STARTUP - LOGGING INITIALIZED <<<", flush=True)


# --- HEALTH & LOG SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Silence server access logs

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        
        # Health Check
        if parsed.path == '/healthz' or parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            health_msg = "Bot is alive! Scraper orchestrator ready."
            self.wfile.write(health_msg.encode('utf-8'))
            return

        # Robot Check
        if parsed.path == '/robots.txt':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"User-agent: *\nDisallow: /")
            return

        # LOGS ENDPOINT (Autonomous Debugging)
        # Usage: /logs?key=SECRET_KEY
        if parsed.path == '/logs':
            file_qs = parse_qs(parsed.query)
            env_key = os.environ.get("LOG_ACCESS_KEY", "debugme")
            user_key = file_qs.get('key', [''])[0]
            
            if user_key != env_key:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Access Denied")
                return

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            
            # Dump buffer
            content = "".join(list(log_buffer))
            self.wfile.write(content.encode('utf-8'))
            return

        # DEBUG SCREENSHOT ENDPOINT
        if parsed.path == '/debug.png':
            try:
                with open("debug_screenshot.png", "rb") as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.end_headers()
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"No screenshot captured yet.")
            return

        # TEST SCRAPE ENDPOINT (Protected)
        # Usage: /test-scrape?query=CS 4349 001&key=SECRET_KEY
        if parsed.path == '/test-scrape':
            file_qs = parse_qs(parsed.query)
            env_key = os.environ.get("LOG_ACCESS_KEY", "debugme")
            user_key = file_qs.get('key', [''])[0]
            
            if user_key != env_key:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Access Denied")
                return
            
            query = file_qs.get('query', ['CS 4349'])[0]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            
            import json
            import traceback
            from src.scraper import get_available_methods
            from src import parser as parser_module
            
            result = {
                "query": query,
                "available_methods": get_available_methods(),
                "method_used": None,
                "success": False,
                "html_length": 0,
                "parsed_rows": 0,
                "error": None
            }
            
            try:
                # Import here to avoid circular dependencies
                from src.scraper import fetch_results_html
                
                html = fetch_results_html(query, headless=True, timeout_ms=30000)
                result["html_length"] = len(html) if html else 0
                
                if html:
                    if "cb-row" in html:
                        rows = parser_module.parse_results_fragment(html)
                        result["parsed_rows"] = len(rows)
                        result["success"] = True
                        result["html_preview"] = html[:500]
                        result["sample_rows"] = [{"label": r.get("label"), "status": r.get("status_text")} for r in rows[:3]]
                    else:
                        result["error"] = "HTML returned but no cb-row elements found (might be CAPTCHA)"
                        result["html_preview"] = html[:500]
                else:
                    result["error"] = "All scraping methods returned empty result"
                    
            except Exception as e:
                result["error"] = str(e)
                result["traceback"] = traceback.format_exc()
            
            self.wfile.write(json.dumps(result, indent=2).encode('utf-8'))
            return

        # STATUS ENDPOINT
        # Usage: /status
        if parsed.path == '/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            
            import json
            from datetime import datetime
            
            status = {
                "bot_status": "online" if bot.is_ready() else "offline",
                "database_connected": db.client is not None,
                "check_loop_running": check_availability_loop.is_running() if 'check_availability_loop' in globals() else False,
                "current_time": datetime.now().isoformat(),
                "health": "ok"
            }
            
            # Try to get scraper status
            try:
                from src.scraper import get_available_methods
                status["available_scrapers"] = get_available_methods()
            except:
                status["available_scrapers"] = []
            
            # Try to get subscription count
            try:
                subs = db.get_subscriptions()
                status["subscription_count"] = len(subs)
                status["total_tracked_courses"] = len(subs.keys())
            except:
                status["subscription_count"] = "unknown"
            
            self.wfile.write(json.dumps(status, indent=2).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    print(f"WEB_SERVER: Starting on 0.0.0.0:{port} ...", flush=True)
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        print(f"WEB_SERVER: LISTENING SUCCESS! Port {port} is open.", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"WEB_SERVER: CRITICAL ERROR binding port: {e}", flush=True)
        # If server fails, we should probably exit to restart container
        os._exit(1) 

# Start server IMMEDIATELY in background
t = threading.Thread(target=start_health_server, daemon=True)
t.start()
time.sleep(1) # Give it a second to print connection status


# --- VIRTUAL DISPLAY MANAGEMENT ---
# Not needed for curl_cffi (Lightweight Requests)
# try:
#     if not os.environ.get("BROWSERLESS_TOKEN"):
#         pass 
#         # print("XVFB: Initializing virtual display (pyvirtualdisplay)...", flush=True)
#         # from pyvirtualdisplay import Display
#         # # Visible=0 means Xvfb (hidden virtual display)
#         # # size matches the Playwright viewport
#         # display = Display(visible=0, size=(1920, 1080))
#         # display.start()
#         # print("XVFB: Virtual display STARTED :0", flush=True)
#         
#         # # Verify DISPLAY env var
#         # print(f"XVFB: DISPLAY={os.environ.get('DISPLAY')}", flush=True)
#     else:
#         print("BROWSERLESS: Token found, skipping local Xvfb start.", flush=True)
# except Exception as e:
#     print(f"XVFB: ERROR starting virtual display: {e}", flush=True)
#     print("XVFB: Continuing anyway (maybe Browserless is used or Xvfb already running?)", flush=True)


# --- BOT IMPORTS ---
print("BOT: Importing heavy libraries...", flush=True)

import json
print("BOT: json imported", flush=True)

from dotenv import load_dotenv
print("BOT: dotenv imported", flush=True)

from datetime import datetime
print("BOT: datetime imported", flush=True)

print("BOT: Importing discord...", flush=True)
import discord
from discord.ext import commands, tasks
print("BOT: discord imported", flush=True)

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("BOT: ERROR - DISCORD_BOT_TOKEN not set!", flush=True)

from src.database import Database
print("BOT: Database schema imported", flush=True)

from src import runner, parser
print("BOT: runner/parser imported", flush=True)

print("BOT: importing scraper orchestrator...", flush=True)
from src.scraper import fetch_results_html
print("BOT: scraper orchestrator imported", flush=True)

print("BOT: Libraries imported.", flush=True)

# Instantiate DB
db = Database()

# Discord Setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@tasks.loop(minutes=15)
async def check_availability_loop():
    print(f"[{datetime.now()}] LOOP: Starting checks...", flush=True)
    try:
        subs = db.get_subscriptions()
        notified = db.get_notified_state()
        labels = list(subs.keys())
        bot_token = os.getenv("DISCORD_BOT_TOKEN")

        if not labels:
            print("LOOP: No subscriptions.", flush=True)
            return

        for label in labels:
            try:
                print(f"CHECK: {label}", flush=True)
                
                # Run sync scraper in executor
                def run_check():
                    # Use headless=False for Playwright stealth mode (runs headful with Xvfb in Docker)
                    return fetch_results_html(label, headless=False, timeout_ms=30000)
                
                html = await bot.loop.run_in_executor(None, run_check)
                rows = parser.parse_results_fragment(html)
                
                info = None
                for r in rows:
                    if r.get("label") == label:
                        info = r
                        break
                
                if info is None:
                    print(f"CHECK: No match found for {label}", flush=True)
                    continue

                should = runner.should_notify(label, info, notified)
                if should:
                    print(f"NOTIFY: Sending alert for {label}", flush=True)
                    runner.notify_users(label, subs[label], info, bot_token)
                    db.update_notified_state(label, info)
                
            except Exception as inner_e:
                print(f"CHECK ERROR {label}: {inner_e}", flush=True)
                
    except Exception as e:
        print(f"LOOP ERROR: {e}", flush=True)

@bot.event
async def on_ready():
    print(f"BOT: Logged in as {bot.user} (ID: {bot.user.id})", flush=True)
    if not check_availability_loop.is_running():
        check_availability_loop.start()
        print("BOT: Check loop started.", flush=True)

    await bot.sync_commands()
    print("BOT: Commands synced.", flush=True)

# --- SLASH COMMANDS ---
@bot.slash_command(name="track")
async def track(ctx, subject: str, number: str, section: str):
    label = f"{subject.upper()} {number} {section}"
    if db.add_subscription(label, str(ctx.author.id)):
        await ctx.respond(f"✅ Tracking **{label}**.", ephemeral=True)
        try: await ctx.author.send(f"Tracking started for **{label}**.")
        except: pass
    else:
        await ctx.respond(f"Already tracking {label}.", ephemeral=True)

@bot.slash_command(name="untrack")
async def untrack(ctx, subject: str, number: str, section: str):
    label = f"{subject.upper()} {number} {section}"
    db.remove_subscription(label, str(ctx.author.id))
    await ctx.respond(f"Stopped tracking **{label}**.", ephemeral=True)

@bot.slash_command(name="list")
async def list_cmd(ctx):
    tracked = db.get_user_subscriptions(str(ctx.author.id))
    if tracked:
        await ctx.respond("Tracking:\n" + "\n".join(tracked), ephemeral=True)
    else:
        await ctx.respond("Not tracking any classes.", ephemeral=True)


if __name__ == "__main__":
    if TOKEN:
        print("BOT: Starting Discord client...", flush=True)
        bot.run(TOKEN)
    else:
        print("BOT: Missing Token, mostly generic server mode.", flush=True)
        # Keep process alive for web logs even if bot fails
        while True: time.sleep(3600)
