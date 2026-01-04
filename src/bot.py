# src/bot.py

import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- EARLY START HEALTH SERVER ---
# Start this immediately to ensure Render detects the open port
# before heavy imports or initialization.

class HealthCheckHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default server logs to keep console clean
        pass

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/healthz' or self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")
            return
            
        if self.path == '/robots.txt':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"User-agent: *\nDisallow: /")
            return

        self.send_response(404)
        self.end_headers()

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting keep-alive server on 0.0.0.0:{port}", flush=True)
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Start server in background thread immediately
t = threading.Thread(target=start_health_server, daemon=True)
t.start()

# --- IMPORTS ---
import json
from dotenv import load_dotenv
from datetime import datetime
import discord
from discord.ext import commands, tasks

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("ERROR: DISCORD_BOT_TOKEN not set in .env", flush=True)
    # Don't raise, just let it fail later or exit, but keep server alive? 
    # Actually, keep server alive so Render doesn't crashloop immediately.
    # But usually we want to fail fast. 

GUILD_ID = None

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

from src.database import Database
from src import runner, parser
from src.checker_playwright import fetch_results_html

# Instantiate DB
db = Database()

@tasks.loop(minutes=15)
async def check_availability_loop():
    print(f"[{datetime.now()}] Starting scheduled availability check...", flush=True)
    try:
        subs = db.get_subscriptions()
        notified = db.get_notified_state()
        labels = list(subs.keys())
        bot_token = os.getenv("DISCORD_BOT_TOKEN")

        if not labels:
            print("No subscriptions to check.", flush=True)
            return

        for label in labels:
            try:
                print(f"Checking label: {label}", flush=True)
                
                # Run Playwright sync code in thread
                def run_check():
                    return fetch_results_html(label, headless=False)
                
                html = await bot.loop.run_in_executor(None, run_check)
                rows = parser.parse_results_fragment(html)
                
                info = None
                for r in rows:
                    if r.get("label") == label:
                        info = r
                        break
                
                if info is None:
                    print(f"No match for {label}", flush=True)
                    continue

                should = runner.should_notify(label, info, notified)
                if should:
                    print(f"Notifying for {label}", flush=True)
                    runner.notify_users(label, subs[label], info, bot_token)
                    db.update_notified_state(label, info)
                
            except Exception as inner_e:
                print(f"Error checking {label}: {inner_e}", flush=True)
                
    except Exception as e:
        print(f"Error in availability loop: {e}", flush=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})", flush=True)
    
    if not check_availability_loop.is_running():
        check_availability_loop.start()
        print("Started 15-minute availability check loop.", flush=True)

    if GUILD_ID:
        await bot.sync_commands(guild=discord.Object(id=GUILD_ID))
    else:
        await bot.sync_commands()
        print("Synced global commands", flush=True)

@bot.slash_command(name="track", description="Track a class and receive a DM when seats open")
async def track(ctx: discord.ApplicationContext, subject: str, number: str, section: str):
    label = f"{subject.upper()} {number} {section}"
    user_id = str(ctx.author.id)
    success = db.add_subscription(label, user_id)
    
    if success:
        await ctx.respond(f"✅ Now tracking **{label}** for you. I will DM you.", ephemeral=True)
        try:
            await ctx.author.send(f"I'll notify you about **{label}**.")
        except discord.Forbidden:
            pass
    else:
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

if __name__ == "__main__":
    if not TOKEN:
        print("Exiting due to missing token.", flush=True)
    else:
        print("Starting bot...", flush=True)
        bot.run(TOKEN)
