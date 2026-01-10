# src/checker_playwright.py
"""
Playwright-based scraper with advanced stealth techniques to bypass CAPTCHA detection.

Uses non-headless mode with Xvfb for maximum stealth. Implements multiple anti-detection
techniques including JavaScript injection, realistic browser fingerprinting, and human-like behavior.
"""

import os
import sys
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from . import parser

# --- Selectors ---
SEARCH_SELECTOR = "#srch"
RESULT_ROW_SELECTOR = "tr.cb-row"

# Stealth JavaScript to inject into pages
STEALTH_JS = """
// Remove webdriver property
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Override plugins to look like a real browser
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});

// Override languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

// Override permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// Mock Chrome runtime
window.chrome = {
    runtime: {}
};

// Override getBattery if it exists
if (navigator.getBattery) {
    navigator.getBattery = () => Promise.resolve({
        charging: true,
        chargingTime: 0,
        dischargingTime: Infinity,
        level: 1
    });
}

// Remove automation indicators
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""


def fetch_results_html(subject_number: str, headless: bool = False, timeout_ms: int = 30000) -> str:
    """
    Fetches the HTML of the search results page using Playwright with stealth techniques.
    
    Args:
        subject_number: The query string (e.g. "CS 4349 001").
        headless: Whether to run headless. For maximum stealth, use False with Xvfb.
        timeout_ms: Timeout in milliseconds.
    
    Returns:
        HTML string containing search results, or empty string on error.
    """
    browserless_token = os.environ.get("BROWSERLESS_TOKEN")
    
    # Determine if we should use headless mode
    # In Docker with Xvfb, we can run headful (headless=False) which is more stealthy
    # Check if DISPLAY is set (Xvfb is running)
    use_headless = headless and not os.environ.get("DISPLAY")
    
    with sync_playwright() as p:
        browser = None
        try:
            if browserless_token:
                # Connect to Browserless.io cloud browser
                print("PLAYWRIGHT: Connecting to Browserless.io...", flush=True)
                ws_endpoint = f"wss://chrome.browserless.io?token={browserless_token}"
                browser = p.chromium.connect_over_cdp(ws_endpoint)
            else:
                # Launch local browser with stealth args
                print(f"PLAYWRIGHT: Launching browser (headless={use_headless})...", flush=True)
                browser = p.chromium.launch(
                    headless=use_headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--disable-site-isolation-trials",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--window-size=1920,1080",
                    ]
                )
            
            # Create context with realistic browser fingerprint
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/Chicago",
                permissions=["geolocation", "notifications"],
                geolocation={"latitude": 32.9858, "longitude": -96.7501},  # UTD coordinates
                color_scheme="light",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Cache-Control": "max-age=0",
                }
            )
            
            page = context.new_page()
            
            # Inject stealth JavaScript before navigation
            page.add_init_script(STEALTH_JS)
            
            # Add realistic mouse movement simulation
            def simulate_human_behavior():
                """Simulate human-like mouse movements and scrolling"""
                try:
                    # Random mouse movement
                    page.mouse.move(
                        random.randint(100, 500),
                        random.randint(100, 500)
                    )
                    time.sleep(random.uniform(0.1, 0.3))
                except:
                    pass
            
            # Navigate to coursebook with realistic delays
            print("PLAYWRIGHT: Navigating to coursebook...", flush=True)
            page.goto(
                "https://coursebook.utdallas.edu/search",
                wait_until="domcontentloaded",
                timeout=timeout_ms
            )
            
            # Wait a bit to simulate human reading
            time.sleep(random.uniform(1.0, 2.0))
            
            # Simulate human behavior
            simulate_human_behavior()
            
            # Wait for search box to be ready
            try:
                print("PLAYWRIGHT: Waiting for search input...", flush=True)
                page.wait_for_selector(SEARCH_SELECTOR, timeout=10000, state="visible")
            except PWTimeout:
                print("PLAYWRIGHT: Search input not found - possible CAPTCHA", flush=True)
                # Check if CAPTCHA is present
                page_content = page.content()
                if "recaptcha" in page_content.lower() or "verify you are a human" in page_content.lower():
                    print("PLAYWRIGHT: CAPTCHA detected!", flush=True)
                return ""
            
            # Click search box with human-like delay
            time.sleep(random.uniform(0.3, 0.7))
            page.click(SEARCH_SELECTOR, delay=random.randint(50, 150))
            
            # Type search query with human-like typing speed
            print(f"PLAYWRIGHT: Typing search query '{subject_number}'...", flush=True)
            page.keyboard.type(subject_number, delay=random.randint(80, 150))
            
            # Small pause before submitting
            time.sleep(random.uniform(0.5, 1.0))
            
            # Submit search
            try:
                submit_button = page.query_selector("button[type='submit']")
                if submit_button:
                    page.click("button[type='submit']", delay=random.randint(50, 100))
                else:
                    page.keyboard.press("Enter")
            except Exception as e:
                print(f"PLAYWRIGHT: Submit failed, trying Enter key: {e}", flush=True)
                page.keyboard.press("Enter")
            
            # Wait for results with realistic delay
            print("PLAYWRIGHT: Waiting for results...", flush=True)
            time.sleep(random.uniform(1.0, 2.0))
            
            try:
                # Wait for results table
                page.wait_for_selector(RESULT_ROW_SELECTOR, timeout=timeout_ms, state="visible")
                
                # Additional wait to ensure page is fully loaded
                time.sleep(random.uniform(0.5, 1.0))
                
                # Simulate scrolling (human behavior)
                page.evaluate("window.scrollTo(0, 300)")
                time.sleep(random.uniform(0.3, 0.6))
                page.evaluate("window.scrollTo(0, 0)")
                
                html = page.content()
                
                # Validate we got actual results
                if "cb-row" in html:
                    print(f"PLAYWRIGHT: ✓ Success! Got {len(html)} bytes of HTML with results", flush=True)
                    return html
                else:
                    print("PLAYWRIGHT: HTML returned but no cb-row elements found", flush=True)
                    return ""
                    
            except PWTimeout:
                print("PLAYWRIGHT: Timeout waiting for results - possible CAPTCHA", flush=True)
                # Check page content for CAPTCHA
                html = page.content()
                if "recaptcha" in html.lower() or "verify you are a human" in html.lower():
                    print("PLAYWRIGHT: CAPTCHA detected in page content!", flush=True)
                return ""
            
        except Exception as e:
            print(f"PLAYWRIGHT: Error scraping {subject_number}: {e}", flush=True)
            import traceback
            print(f"PLAYWRIGHT: Traceback: {traceback.format_exc()}", flush=True)
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
    
    # Use headless=False for maximum stealth
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
