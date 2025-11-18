# src/checker_playwright.py
"""
Playwright-based checker that uses src.parser for parsing logic.

Usage:
  python src/checker_playwright.py CS 4349 003
"""

import sys
import re
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from . import parser
from . import notifier


# --- Edit only if selector changes ---
SEARCH_SELECTOR = "#srch"
RESULT_ROW_SELECTOR = "tr.cb-row"
# ------------------------------------

# import our parser module (make sure src/parser.py exists)
from . import parser

def fetch_results_html(subject_number: str, headless: bool = False, timeout_ms: int = 20000) -> str:
    
    # with statement allows for broswer to run and then close in one block
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        page.set_viewport_size({"width": 1280, "height": 800})

        # debug logs from the page (lambda is basically mini function)
        page.on("console", lambda msg: print("PAGE LOG:", msg.text))
        page.on("pageerror", lambda err: print("PAGE ERROR:", err))

        page.goto("https://coursebook.utdallas.edu/search", timeout=timeout_ms)

        try:
            page.wait_for_selector(SEARCH_SELECTOR, timeout=5000)
        except PWTimeout:
            print(f"Search input {SEARCH_SELECTOR} not found")
            browser.close()
            return ""

        # use a page click and type in the class into the search box,
        # then in the try and except we use
        # the "click" first uses a backend css selector to directly 
        # tell the html to submit,
        # if that doesn't work, then we just provide an enter key
        page.click(SEARCH_SELECTOR)
        page.keyboard.type(subject_number, delay=100)
        try:
            page.click("button[type='submit']", timeout=3000)
        except Exception:
            page.keyboard.press("Enter")

        # uses playwright feature to return the global variable resultRow
        # unless the timeout time is reached, specifically, the code is 
        # waiting for the matching variable to appear in the website data
        # if it is, then we move to the except block
        try:
            page.wait_for_selector(RESULT_ROW_SELECTOR, timeout=timeout_ms)
        except PWTimeout:
            print("No results found; saving debug screenshot and html.")
            page.screenshot(path="debug_screenshot.png")
            open("debug_page.html", "w", encoding="utf-8").write(page.content())
            browser.close()
            return ""

        html = page.content()
        browser.close()
        return html


def main(argv):
    if len(argv) != 4:
        print("Usage: python src/checker_playwright.py SUBJECT NUMBER SECTION")
        print("Example: python -m src.checker_playwright CS 4349 003")
        return

    subject = argv[1].upper()
    number = argv[2]
    section = argv[3].zfill(3)
    query = f"{subject} {number}"
    target_label = f"{subject} {number}.{section}"

    #generic terminal output
    print("Searching for:", query)
    html = fetch_results_html(query, headless=False)  # headless=False so you can watch it
    if not html:
        print("No HTML returned. See messages above for clues.")
        return

    # use parser to extract structured info
    rows = parser.parse_results_fragment(html, row_selector=RESULT_ROW_SELECTOR)
    print(f"Parsed {len(rows)} rows")

    match = None
    for info in rows:
        # print summary line for debugging, but also prints 
        # out all the info for the class and updates match to be set
        # to the info obtained
        print(info.get("label"), "-", info.get("status_text"), "-", (f"{info.get('enrolled')}/{info.get('capacity')}" if info.get('enrolled') is not None else ("avail:"+str(info.get('seats_available')) if info.get('seats_available') is not None else "")))
        if info.get("label") and info["label"].startswith(target_label):
            match = info
            break

    # saying if "not match" is true, which really means 
    # that match is still set to None, then run the if
    if not match:
        print("Target section not found in results.")
        return

    print("\nMATCH:", match)
    open_bool = parser.is_section_open(match)
    print("Open status:", open_bool)

    label = match.get("label") or "unknown"

    if open_bool:
        print(">>> OPEN SPOT FOUND!")
        try:
            # Ask notifier whether we should notify (avoids duplicate spam)
            if notifier.should_notify(label, True):
                sent = notifier.notify_open(match)
                if sent:
                    notifier.mark_notified(label, True)
                    print("Notification sent.")
                else:
                    print("Notification failed (POST returned error).")
            else:
                print("Already notified recently; skipping notification.")
        except Exception as e:
            # Defensive: don't crash the checker if notifier has an issue
            print("Notifier error:", repr(e))
    else:
        # record closed state so that a future open will notify
        try:
            notifier.mark_notified(label, False)
        except Exception as e:
            print("Notifier mark-notified error:", repr(e))
        print("No open spot found (considered closed/full).")



if __name__ == "__main__":
    main(sys.argv)
