from playwright.sync_api import sync_playwright
import time

def check_browser_health():
    print("--- STARTING HEALTH CHECK ---")
    try:
        with sync_playwright() as p:
            print("Launching browser...")
            # Use the same args we use in production to test effectively
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox", 
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            print("Browser launched.")
            page = browser.new_page()
            
            # Test 1: Simple static site
            print("Test 1: example.com")
            page.goto("https://example.com")
            print(f"Title: {page.title()}")
            
            # Test 2: UTD Coursebook Root (to check if IP is blocked)
            print("Test 2: coursebook.utdallas.edu")
            page.goto("https://coursebook.utdallas.edu/")
            print(f"Title: {page.title()}")
            
            # Test 3: Check for evasion leak (navigator.webdriver)
            webdriver = page.evaluate("navigator.webdriver")
            print(f"navigator.webdriver is: {webdriver}")  # Should be False or Undefined if evasion works
            
            browser.close()
            print("--- HEALTH CHECK PASSED ---")
            return True
    except Exception as e:
        print(f"--- HEALTH CHECK FAILED: {e} ---")
        return False

if __name__ == "__main__":
    check_browser_health()
