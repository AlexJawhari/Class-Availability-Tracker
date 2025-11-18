# src/bot.py

import os
import json
from dotenv import load_dotenv
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

SUBS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "subscriptions.json")

def load_subs():
    try:
        with open(SUBS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_subs(data):
    with open(SUBS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
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
    subs = load_subs()
    user_id = str(ctx.author.id)
    if label not in subs:
        subs[label] = []
    if user_id in subs[label]:
        await ctx.respond(f"You're already tracking {label}.", ephemeral=True)
        return
    subs[label].append(user_id)
    save_subs(subs)
    await ctx.respond(f"✅ Now tracking **{label}** for you. I will DM you when it opens.", ephemeral=True)
    try:
        await ctx.author.send(f"I'll notify you about **{label}**. Use /untrack {subject} {number} {section} to stop.")
    except discord.Forbidden:
        pass

@bot.slash_command(name="untrack", description="Stop tracking a class")
async def untrack(ctx: discord.ApplicationContext, subject: str, number: str, section: str):
    label = f"{subject.upper()} {number} {section}"
    subs = load_subs()
    user_id = str(ctx.author.id)
    if label not in subs or user_id not in subs[label]:
        await ctx.respond(f"You were not tracking {label}.", ephemeral=True)
        return
    subs[label].remove(user_id)
    if not subs[label]:
        subs.pop(label)
    save_subs(subs)
    await ctx.respond(f"Stopped tracking **{label}**.", ephemeral=True)

@bot.slash_command(name="list", description="List classes you are tracking")
async def list_cmd(ctx: discord.ApplicationContext):
    subs = load_subs()
    user_id = str(ctx.author.id)
    tracked = [lbl for lbl, users in subs.items() if user_id in users]
    if not tracked:
        await ctx.respond("You are not tracking any classes.", ephemeral=True)
    else:
        formatted = "\n".join(tracked)
        await ctx.respond(f"You're tracking these classes:\n{formatted}", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
