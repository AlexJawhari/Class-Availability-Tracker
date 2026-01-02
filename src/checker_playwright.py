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


# --- Edit only if selector changes ---
SEARCH_SELECTOR = "#srch"
RESULT_ROW_SELECTOR = "tr.cb-row"
# ------------------------------------

# import our parser module (make sure src/parser.py exists)
from . import parser

def fetch_results_html(subject_number: str, headless: bool = True, timeout_ms: int = 20000) -> str:
    
    # with statement allows for broswer to run and then close in one block
    with sync_playwright() as p:
        # Launch with a real user agent to avoid detection/rendering issues
        browser = p.chromium.launch(headless=headless)
        # Create a context with user agent
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()

        page.set_viewport_size({"width": 1280, "height": 800})

        # debug logs from the page (lambda is basically mini function)
        page.on("console", lambda msg: print("PAGE LOG:", msg.text))
        # page.on("pageerror", lambda err: print("PAGE ERROR:", err)) # Reduce noise

        try:
            page.goto("https://coursebook.utdallas.edu/search", timeout=timeout_ms)
            
            # Wait for search box
            page.wait_for_selector(SEARCH_SELECTOR, state="visible", timeout=10000)
            
            # Click and type
            page.click(SEARCH_SELECTOR)
            page.keyboard.type(subject_number, delay=100)
            
            # Press enter (more reliable than clicking generic buttons sometimes)
            page.keyboard.press("Enter")
            
            # Wait for results
            # The site might be slow, so we give it a moment
            page.wait_for_selector(RESULT_ROW_SELECTOR, state="attached", timeout=timeout_ms)
            
            # Add a small buffer for JS to settle
            page.wait_for_timeout(2000)

            html = page.content()
            browser.close()
            return html
            
        except Exception as e:
            print(f"Scrape error for {subject_number}: {e}")
            try:
                page.screenshot(path="debug_error.png")
            except:
                pass
            browser.close()
            return ""


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
        # print summary line for debugging
        print(info.get("label"), "-", info.get("status_text"))
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
    
    # Note: Notification logic is handled by runner.py / bot.py now.
    # This script is primarily for testing the scraper logic.



if __name__ == "__main__":
    main(sys.argv)
