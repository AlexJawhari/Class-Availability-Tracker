# src/bot.py

import os
import json
from dotenv import load_dotenv
from datetime import datetime
import discord
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN not set in .env")

# Set this to your test guild to speed up command sync (optional)
GUILD_ID = None  # e.g. 123456789012345678

intents = discord.Intents.default()
# If you need message content (probably not) you could do:
# intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

from src.database import Database

# Instantiate DB
db = Database()

# --- BACKGROUND TASK: CHECKER ---
# This allows the bot process to also handle the 15-minute checks
from discord.ext import tasks

# We need to import the logic from runner, but runner.py is currently designed as a script.
# We will duplicate the core logic or refactor runner.py to export a 'check_all' function.
# For simplicity and clean code, we'll import the core functions from runner if possible,
# or better yet, we'll implement a clean check loop here that re-uses the components.
from src import runner, parser
from src.checker_uc import fetch_results_html

@tasks.loop(minutes=15)
async def check_availability_loop():
    print(f"[{datetime.now()}] Starting scheduled availability check...")
    try:
        # Load state
        subs = db.get_subscriptions()
        notified = db.get_notified_state()
        labels = list(subs.keys())
        bot_token = os.getenv("DISCORD_BOT_TOKEN")

        if not labels:
            print("No subscriptions to check.")
            return

        for label in labels:
            try:
                # Fix: Run Playwright sync code in a separate thread to avoid blocking asyncio loop
                # and to satisfy Playwright's safety checks.
                print(f"Checking label: {label}")
                
                # Create a wrapper to call the sync function with arguments
                def run_check():
                    return fetch_results_html(label, headless=True)
                
                html = await bot.loop.run_in_executor(None, run_check)
                rows = parser.parse_results_fragment(html)
                
                info = None
                for r in rows:
                    if r.get("label") == label:
                        info = r
                        break
                
                if info is None:
                    print(f"No match for {label}")
                    continue

                should = runner.should_notify(label, info, notified)
                if should:
                    print(f"Notifying for {label}")
                    # Use runner's notifier which uses requests (sync)
                    # or better, since we are in the bot, we can use the bot to DM!
                    # But to keep logic consistent with runner.py, let's just reuse the
                    # existing notification helper or do it async way.
                    runner.notify_users(label, subs[label], info, bot_token)
                    db.update_notified_state(label, info)
                
            except Exception as inner_e:
                print(f"Error checking {label}: {inner_e}")
                
    except Exception as e:
        print(f"Error in availability loop: {e}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    
    # Start the loop if not already running
    if not check_availability_loop.is_running():
        check_availability_loop.start()
        print("Started 15-minute availability check loop.")

    # Optionally sync commands:
    if GUILD_ID:
        # Sync only to a specific guild
        await bot.sync_commands(guild=discord.Object(id=GUILD_ID))
        print(f"Synced commands to guild {GUILD_ID}")
    else:
        await bot.sync_commands()
        print("Synced global commands")

@bot.slash_command(name="track", description="Track a class and receive a DM when seats open")
async def track(ctx: discord.ApplicationContext, subject: str, number: str, section: str):
    label = f"{subject.upper()} {number} {section}"
    user_id = str(ctx.author.id)
    
    success = db.add_subscription(label, user_id)
    
    if success:
        await ctx.respond(f"✅ Now tracking **{label}** for you. I will DM you when it opens.", ephemeral=True)
        try:
            await ctx.author.send(f"I'll notify you about **{label}**. Use /untrack {subject} {number} {section} to stop.")
        except discord.Forbidden:
            pass
    else:
         # Rough assumption that failure meant duplicate here (upsert handles it gracefully usually)
         # But effectively if it returns true, we good.
         await ctx.respond(f"You are already tracking {label} (or DB error).", ephemeral=True)


@bot.slash_command(name="untrack", description="Stop tracking a class")
async def untrack(ctx: discord.ApplicationContext, subject: str, number: str, section: str):
    label = f"{subject.upper()} {number} {section}"
    user_id = str(ctx.author.id)
    
    db.remove_subscription(label, user_id)
    await ctx.respond(f"Stopped tracking **{label}**.", ephemeral=True)

@bot.slash_command(name="list", description="List classes you are tracking")
async def list_cmd(ctx: discord.ApplicationContext):
    user_id = str(ctx.author.id)
    tracked = db.get_user_subscriptions(user_id)
    
    if not tracked:
        await ctx.respond("You are not tracking any classes.", ephemeral=True)
    else:
        formatted = "\n".join(tracked)
        await ctx.respond(f"You're tracking these classes:\n{formatted}", ephemeral=True)


# --- RENDER KEEPALIVE SERVER ---
# Render expects a web service to bind to the PORT env var.
# We run a simple HTTP server in a separate thread to say "I'm alive".
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/robots.txt':
            self.send_response(200)
            self.send_header('Content-context', 'text/plain')
            self.end_headers()
            self.wfile.write(b"User-agent: *\nDisallow: /")
            return

        if self.path == '/debug.png':
            if os.path.exists("debug_last_run.png"):
                self.send_response(200)
                self.send_header('Content-context', 'image/png')
                self.end_headers()
                with open("debug_last_run.png", "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"No debug image found.")
            return
            
        if self.path == '/healthz' or self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")
            return
            
        self.send_response(404)
        self.end_headers()

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Starting keep-alive server on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    # Start the HTTP server in a background thread
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    
    bot.run(TOKEN)
