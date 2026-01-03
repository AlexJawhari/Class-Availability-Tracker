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

def fetch_results_html(subject_number: str, headless: bool = True, timeout_ms: int = 30000) -> str:
    
    # with statement allows for broswer to run and then close in one block
    with sync_playwright() as p:
        # Launch with flags to avoid detection and improve stability in Docker
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox", 
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        
        # Create a context with real-user characteristics
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/Chicago"
        )
        
        # KEY FIX: Inject stealth scripts to hide "Headless" status which causes the 'js_options' error
        # AND override Client Hints (uafvl) to prevent "HeadlessChrome" from appearing in analytics/captcha checks.
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.navigator.chrome = {
                runtime: {},
                // test
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            // Mock Client Hints to pretend to be a regular Google Chrome on Windows
            Object.defineProperty(navigator, 'userAgentData', {
                get: () => ({
                    brands: [
                        { brand: "Not_A Brand", version: "8" },
                        { brand: "Chromium", version: "120" },
                        { brand: "Google Chrome", version: "120" }
                    ],
                    mobile: false,
                    platform: "Windows"
                })
            });
        """)
        
        page = context.new_page()

        # debug logs from the page
        page.on("console", lambda msg: print("PAGE LOG:", msg.text))
        
        # Capture network requests to reverse-engineer the API
        page.on("request", lambda request: print(">> REQUEST:", request.method, request.url))

        try:
            page.goto("https://coursebook.utdallas.edu/search", timeout=timeout_ms)
            page.wait_for_load_state("domcontentloaded")
            
            # Wait for search box with safety buffer
            page.wait_for_selector(SEARCH_SELECTOR, state="visible", timeout=10000)
            
            # Interact to mimic human speed slightly
            page.click(SEARCH_SELECTOR)
            page.wait_for_timeout(200)
            page.keyboard.type(subject_number, delay=100)
            page.wait_for_timeout(200)
            page.keyboard.press("Enter")
            
            # Wait for results
            # We wait for the row to appear.
            # Using 'domcontentloaded' or 'networkidle' can help if the site uses complex hydration
            try:
                page.wait_for_selector(RESULT_ROW_SELECTOR, state="attached", timeout=timeout_ms)
            except PWTimeout:
                # Retry strategy: sometimes hitting enter again helps if the first one was swallowed
                print("Retry: Pressing Enter again...")
                page.keyboard.press("Enter")
                page.wait_for_selector(RESULT_ROW_SELECTOR, state="attached", timeout=10000)

            # Extra buffer for table render
            page.wait_for_timeout(1000)

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
