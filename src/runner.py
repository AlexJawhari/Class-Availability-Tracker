# src/runner.py

import os
import json
from datetime import datetime, timezone

from src import parser
from src.checker_playwright import fetch_results_html  # adjust import per your existing code
import discord
import time
from . import parser
from .checker_playwright import fetch_results_html


# Path to subscription file (same as bot used)
SUBS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "subscriptions.json")
NOTIFIED_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "notified.json")

def load_subscriptions():
    try:
        with open(SUBS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_notified(state):
    with open(NOTIFIED_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def load_notified():
    try:
        with open(NOTIFIED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def should_notify(label, info, notified_state, backoff_seconds=3600):
    """
    Decide whether to notify based on previous state.
    """
    entry = notified_state.get(label)
    now = datetime.now(timezone.utc)
    if entry is None:
        return True
    last = entry.get("last_notified")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except Exception:
        return True
    elapsed = (now - last_dt).total_seconds()
    if elapsed >= backoff_seconds:
        # also only notify if status changed or seats opened
        prev_status = entry.get("last_status")
        prev_enrolled = entry.get("enrolled")
        # If status was closed and now open, or enrolled < capacity
        if info.get("status_text") != prev_status or (info.get("enrolled") is not None and
                                                      entry.get("enrolled") is not None and
                                                      info.get("enrolled") < entry.get("enrolled")):
            return True
    return False

def mark_notified(label, info, notified_state):
    entry = {
        "last_notified": datetime.now(timezone.utc).isoformat(),
        "last_status": info.get("status_text"),
        "enrolled": info.get("enrolled")
    }
    notified_state[label] = entry
    save_notified(notified_state)

def notify_users(label, user_ids, info, bot_token):
    """
    Use Discord REST API to DM users. (Avoid importing heavy discord voice modules.)
    """
    import requests
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }
    for uid in user_ids:
        # Step 1: open DM channel
        r = requests.post("https://discord.com/api/v10/users/@me/channels",
                          headers=headers,
                          json={"recipient_id": uid})
        if r.status_code != 200:
            print("Failed to open DM for", uid, r.status_code, r.text)
            continue
        dm = r.json()
        channel_id = dm.get("id")
        if not channel_id:
            continue
        # Step 2: send message
        msg = f"🔔 **{label}** is now open or changed!\nStatus: {info.get('status_text')}\nEnrolled: {info.get('enrolled')}/{info.get('capacity')}"
        r2 = requests.post(f"https://discord.com/api/v10/channels/{channel_id}/messages",
                           headers=headers,
                           json={"content": msg})
        if r2.status_code != 200:
            print("Failed sending DM to", uid, r2.status_code, r2.text)
        time.sleep(0.5)  # throttle

def main():
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        print("DISCORD_BOT_TOKEN not set; abort.")
        return

    subs = load_subscriptions()
    notified = load_notified()
    labels = list(subs.keys())
    for label in labels:
        try:
            print("Checking label:", label)
            html = fetch_results_html(label)
            rows = parser.parse_results_fragment(html)
            info = None
            for r in rows:
                if r.get("label") == label:
                    info = r
                    break
            print("Parsed info:", info)
            if info is None:
                print("No matching section row for", label)
                continue
            # show status open/closed
            is_open = parser.is_section_open(info)
            print(f"is_section_open: {is_open}, status_text: {info.get('status_text')}, enrolled/capacity: {info.get('enrolled')}/{info.get('capacity')}")
            if should_notify(label, info, notified):
                print("Should notify for label:", label)
                notify_users(label, subs[label], info, bot_token)
                mark_notified(label, info, notified)
            else:
                print("Not notifying for label (backoff or no change).")
        except Exception as e:
            print("Error checking", label, e)

'''
    # dedupe labels
    labels = list(subs.keys())
    for label in labels:
        try:
            # fetch HTML and parse
            html = fetch_results_html(label)  # you may need to convert label to subject+number form
            rows = parser.parse_results_fragment(html)
            # find the matching section
            info = None
            for r in rows:
                if r.get("label") == label:
                    info = r
                    break
            if info is None:
                continue
            # decision
            if should_notify(label, info, notified):
                notify_users(label, subs[label], info, bot_token)
                mark_notified(label, info, notified)
        except Exception as e:
            print("Error checking", label, e)
'''

if __name__ == "__main__":
    main()
