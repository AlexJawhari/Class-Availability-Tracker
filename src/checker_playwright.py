
import sys
import re
import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from . import parser

# --- Edit only if selector changes ---
SEARCH_SELECTOR = "#srch"
RESULT_ROW_SELECTOR = "tr.cb-row"
# ------------------------------------

def fetch_results_html(subject_number: str, headless: bool = False, timeout_ms: int = 30000) -> str:
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
        # Try to load session state if available
        # We look for the file relative to the script or CWD
        import os
        storage_state_path = "src/session_state.json"
        
        # If running as module from root, src/session_state.json is correct if CWD is root.
        # Check if file exists to avoid error spam
        if os.path.exists(storage_state_path):
             pass
        else:
             # Fallback to absolute path or just let it fail gracefully
             pass

        try:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/Chicago",
                storage_state=storage_state_path
            )
            print(f"Loaded session state from {storage_state_path}")
        except Exception:
            print(f"Could not load session state from {storage_state_path}, starting fresh.")
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/Chicago"
            )

        
        page = context.new_page()

        try:
            page.goto("https://coursebook.utdallas.edu/search", timeout=timeout_ms)
            page.wait_for_load_state("domcontentloaded")
            
            # Wait for search box with safety buffer
            # Random initial delay
            time.sleep(2)

            page.wait_for_selector(SEARCH_SELECTOR, state="visible", timeout=10000)
            
            # Interact 
            page.click(SEARCH_SELECTOR)
            time.sleep(0.5)
            page.keyboard.type(subject_number, delay=100)
            time.sleep(0.5)
            page.keyboard.press("Enter")
            
            # Wait for results
            try:
                page.wait_for_selector(RESULT_ROW_SELECTOR, state="attached", timeout=timeout_ms)
            except PWTimeout:
                # Retry strategy
                print("Retry 1: Pressing Enter again...")
                page.keyboard.press("Enter")
                page.wait_for_selector(RESULT_ROW_SELECTOR, state="attached", timeout=15000)

            # Extra buffer for table render
            time.sleep(1)

            html = page.content()
            # Capture success screenshot too
            page.screenshot(path="debug_last_run.png")
            browser.close()
            return html
            
        except Exception as e:
            print(f"Scrape error for {subject_number}: {e}")
            try:
                # Save screenshot to a file that bot.py can serve
                page.screenshot(path="debug_last_run.png")
                print("Saved failure screenshot to debug_last_run.png")
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


if __name__ == "__main__":
    main(sys.argv)
