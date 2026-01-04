# src/checker_playwright.py
"""
Playwright-based checker with Browserless.io cloud browser support.

Supports both:
- Browserless.io cloud browser (when BROWSERLESS_TOKEN is set)
- Local browser with Xvfb (when running in Docker without token)

Usage:
  python -m src.checker_playwright CS 4349 003
"""

import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from . import parser

# --- Selectors ---
SEARCH_SELECTOR = "#srch"
RESULT_ROW_SELECTOR = "tr.cb-row"


def fetch_results_html(subject_number: str, headless: bool = False, timeout_ms: int = 20000) -> str:
    """
    Fetches the HTML of the search results page.
    
    If BROWSERLESS_TOKEN is set, connects to Browserless.io cloud browser.
    Otherwise, launches a local browser (headless or headful).
    
    Args:
        subject_number: The query string (e.g. "CS 4349").
        headless: Whether to run headless (only applies to local browser).
        timeout_ms: Timeout in milliseconds.
    """
    browserless_token = os.environ.get("BROWSERLESS_TOKEN")
    
    with sync_playwright() as p:
        browser = None
        try:
            if browserless_token:
                # Connect to Browserless.io cloud browser
                print(f"Connecting to Browserless.io...")
                ws_endpoint = f"wss://chrome.browserless.io?token={browserless_token}"
                browser = p.chromium.connect_over_cdp(ws_endpoint)
            else:
                # Launch local browser (headful in Xvfb for Docker, or visible locally)
                print(f"Launching local browser (headless={headless})...")
                browser = p.chromium.launch(headless=headless)
            
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})
            
            # Debug logs
            page.on("console", lambda msg: print("PAGE LOG:", msg.text))
            
            # Navigate to coursebook
            print(f"Navigating to coursebook...")
            page.goto("https://coursebook.utdallas.edu/search", timeout=timeout_ms)
            
            # Wait for search box
            try:
                page.wait_for_selector(SEARCH_SELECTOR, timeout=5000)
            except PWTimeout:
                print(f"Search input {SEARCH_SELECTOR} not found")
                return ""
            
            # Type search query
            page.click(SEARCH_SELECTOR)
            page.keyboard.type(subject_number, delay=100)
            
            # Submit search
            try:
                page.click("button[type='submit']", timeout=3000)
            except Exception:
                page.keyboard.press("Enter")
            
            # Wait for results
            print(f"Waiting for results...")
            try:
                page.wait_for_selector(RESULT_ROW_SELECTOR, timeout=timeout_ms)
            except PWTimeout:
                print("No results found (CAPTCHA likely served)")
                try:
                    page.screenshot(path="debug_screenshot.png")
                except:
                    pass
                return ""
            
            html = page.content()
            print(f"Got {len(html)} bytes of HTML")
            return html
            
        except Exception as e:
            print(f"Scrape error for {subject_number}: {e}")
            return ""
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass


def main(argv):
    """Test the scraper directly."""
    if len(argv) < 2:
        print("Usage: python -m src.checker_playwright 'CS 4349'")
        print("  or:  python -m src.checker_playwright CS 4349 003")
        return
    
    # Build query from args
    if len(argv) == 4:
        subject = argv[1].upper()
        number = argv[2]
        section = argv[3].zfill(3)
        query = f"{subject} {number}"
        target_label = f"{subject} {number} {section}"
    else:
        query = " ".join(argv[1:])
        target_label = None
    
    print(f"Searching for: {query}")
    
    # Use headless=False for local testing to see what's happening
    html = fetch_results_html(query, headless=False)
    
    if not html:
        print("No HTML returned.")
        return
    
    rows = parser.parse_results_fragment(html, row_selector=RESULT_ROW_SELECTOR)
    print(f"Parsed {len(rows)} rows")
    
    for info in rows:
        label = info.get("label", "?")
        status = info.get("status_text", "?")
        enrolled = info.get("enrolled")
        capacity = info.get("capacity")
        seats = info.get("seats_available")
        
        extra = ""
        if enrolled is not None and capacity is not None:
            extra = f"{enrolled}/{capacity}"
        elif seats is not None:
            extra = f"avail:{seats}"
            
        print(f"  {label} - {status} - {extra}")
        
        if target_label and label and label.startswith(target_label):
            print(f"\nMATCH: {info}")
            print(f"Open: {parser.is_section_open(info)}")


if __name__ == "__main__":
    main(sys.argv)
