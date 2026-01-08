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
            self.end_headers()
            self.wfile.write(b"Bot is alive! Xvfb managed by Python.")
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
            # Simple security: Check env var 'LOG_ACCESS_KEY' or default to a known dev key if not set
            # For now, let's use a simple hardcoded fallback if env not set, OR just allow public read if mostly harmless logs?
            # Better to require a key. 
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
# Manage Xvfb here instead of Dockerfile CMD
# Only needed if NOT using Browserless.io
try:
    if not os.environ.get("BROWSERLESS_TOKEN"):
        print("XVFB: Initializing virtual display (pyvirtualdisplay)...", flush=True)
        from pyvirtualdisplay import Display
        # Visible=0 means Xvfb (hidden virtual display)
        # size matches the Playwright viewport
        display = Display(visible=0, size=(1920, 1080))
        display.start()
        print("XVFB: Virtual display STARTED :0", flush=True)
        
        # Verify DISPLAY env var
        print(f"XVFB: DISPLAY={os.environ.get('DISPLAY')}", flush=True)
    else:
        print("BROWSERLESS: Token found, skipping local Xvfb start.", flush=True)
except Exception as e:
    print(f"XVFB: ERROR starting virtual display: {e}", flush=True)
    print("XVFB: Continuing anyway (maybe Browserless is used or Xvfb already running?)", flush=True)


# --- BOT IMPORTS ---
print("BOT: Importing heavy libraries...", flush=True)
import json
from dotenv import load_dotenv
from datetime import datetime
import discord
from discord.ext import commands, tasks

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("BOT: ERROR - DISCORD_BOT_TOKEN not set!", flush=True)

from src.database import Database
# Import checker late to prevent early playwright init?
# Actually good to import now.
from src import runner, parser
from src.checker_playwright import fetch_results_html

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
                    # headless=False works with Xvfb
                    return fetch_results_html(label, headless=False)
                
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
