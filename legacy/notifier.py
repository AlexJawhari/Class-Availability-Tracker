# src/notifier.py
"""
Discord webhook notifier + simple file-based notification state.

Usage:
- Create a .env file in the project root with:
    DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
- Make sure .env is in .gitignore (do not commit it).
- pip install requests python-dotenv

API:
- notify_open(section_info: dict) -> bool
- should_notify(label: str, is_open: bool) -> bool
- mark_notified(label: str, is_open: bool)
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Load .env (must be called before os.getenv)
load_dotenv()

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# State file to avoid duplicate notifications
STATE_PATH = Path("data/notified.json")
RENOTIFY_AFTER = timedelta(hours=1)  # re-notify every hour if still open (adjustable)


def _post_to_discord(payload: dict) -> bool:
    if not WEBHOOK_URL:
        raise RuntimeError("DISCORD_WEBHOOK_URL not set in environment")
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
    # Discord sometimes returns 204 (no content) for success, sometimes 200
    return resp.status_code in (200, 204)


def notify_open(section_info: dict) -> bool:
    """
    Send a Discord embed describing the open class.
    Returns True on successful POST (status 200 or 204).
    """
    label = section_info.get("label") or "<unknown>"
    enrolled = section_info.get("enrolled")
    capacity = section_info.get("capacity")
    seats_available = section_info.get("seats_available")
    raw = (section_info.get("raw") or "").strip()

    # Human-friendly seats text
    if seats_available is not None:
        seats_field = f"{seats_available} seats available"
    elif enrolled is not None and capacity is not None:
        seats_field = f"{enrolled}/{capacity} enrolled"
    else:
        seats_field = "unknown"

    # Compose short description from raw; try to extract instructor/time/room if available
    # (raw is a fallback; prefer structured fields if you add them later)
    snippet = raw
    if len(snippet) > 400:
        snippet = snippet[:400] + "..."

    # Optional: a link to the class detail page if parser provides it later
    detail_url = section_info.get("detail_url")

    # Build an embed object
    embed = {
        "title": f"Class open: {label}",
        "description": snippet or "No extra info",
        "color": 0x2ECC71,  # green
        "fields": [
            {"name": "Seats", "value": seats_field, "inline": True},
            {"name": "Checked (UTC)", "value": datetime.utcnow().isoformat() + "Z", "inline": True},
        ],
        "footer": {"text": "Class Availability Tracker"},
    }
    if detail_url:
        # Discord makes the embed title clickable if you include "url" at the top-level
        embed["url"] = detail_url

    payload = {"embeds": [embed]}

    return _post_to_discord(payload)

"""
def notify_open(section_info: dict) -> bool:
    label = section_info.get("label") or "<unknown>"
    enrolled = section_info.get("enrolled")
    capacity = section_info.get("capacity")
    seats_available = section_info.get("seats_available")
    raw = section_info.get("raw", "")

    # Build a simple, human-friendly message using Markdown
    # Bold title, then a short bullet / inline summary, then a one-line raw snippet.
    lines = []
    lines.append(f"**Class open: {label}**")                     # bold title
    if seats_available is not None:
        lines.append(f"- Seats available: **{seats_available}**")
    elif enrolled is not None and capacity is not None:
        lines.append(f"- Enrolled: **{enrolled}/{capacity}**")
    else:
        lines.append("- Seats: **unknown**")

    # Optional extra info (trim to keep message tidy)
    extra = raw.strip()
    if extra:
        # use a single short snippet (avoid huge messages)
        snippet = (extra[:300] + "...") if len(extra) > 300 else extra
        lines.append(f"> {snippet}")   # blockquote for readability

    lines.append(f"_Checked (UTC): {datetime.utcnow().isoformat()}Z_")

    content = "\n".join(lines)
    payload = {"content": content}
    return _post_to_discord(payload)




def notify_open(section_info: dict) -> bool:
    ""
    Send a simple content message to Discord containing useful info about the section.
    Returns True on success, False otherwise.
    ""
    label = section_info.get("label") or "<unknown>"
    enrolled = section_info.get("enrolled")
    capacity = section_info.get("capacity")
    seats_available = section_info.get("seats_available")

    title = f"Class open: {label}"
    details_lines = []

    if seats_available is not None:
        details_lines.append(f"{seats_available} seats available")
    elif enrolled is not None and capacity is not None:
        details_lines.append(f"{enrolled}/{capacity} enrolled")
    # include a short raw snippet for debugging/context
    if section_info.get("raw"):
        details_lines.append(section_info["raw"][:250])

    details_lines.append(f"Checked at (UTC): {datetime.utcnow().isoformat()}Z")
    content = f"**{title}**\n" + "\n".join(details_lines)

    payload = {"content": content}
    return _post_to_discord(payload)
"""



# --- Simple file-based state helpers ---


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state), encoding="utf-8")


def should_notify(label: str, is_open: bool) -> bool:
    """
    Decide whether to send a notification for this label.
    - If we've never notified about this label -> True
    - If status changed since last notification -> True
    - If still open but last notification was > RENOTIFY_AFTER -> True
    - Otherwise -> False
    """
    state = _load_state()
    entry = state.get(label)
    now = datetime.utcnow()
    if not entry:
        return True
    last_status = entry.get("last_status")  # "open" or "closed"
    last_notified_iso = entry.get("last_notified")
    try:
        last_notified = datetime.fromisoformat(last_notified_iso)
    except Exception:
        # if parsing fails, be conservative and notify
        return True

    if last_status != ("open" if is_open else "closed"):
        return True

    if is_open and (now - last_notified > RENOTIFY_AFTER):
        return True

    return False


def mark_notified(label: str, is_open: bool):
    """
    Record that we notified (or marked) the given label with the given state.
    """
    state = _load_state()
    state[label] = {
        "last_status": "open" if is_open else "closed",
        "last_notified": datetime.utcnow().isoformat()
    }
    _save_state(state)
