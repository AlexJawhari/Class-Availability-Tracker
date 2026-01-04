
import sys
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from . import parser

# --- Constants ---
SEARCH_SELECTOR = "#srch"
RESULT_ROW_SELECTOR = "tr.cb-row"

def fetch_results_html(subject_number: str, headless: bool = False, timeout_ms: int = 30000) -> str:
    """
    Fetches the HTML of the search results page using undetected_chromedriver.
    
    Args:
        subject_number: The query string (e.g. "CS 4349").
        headless: Whether to run headless. 
                  NOTE: undetected_chromedriver 2.x+ handles headless differently.
                  With Xvfb (on specific environments), we often just run headful 
                  inside Xvfb rather than using the --headless flag, to be safer.
        timeout_ms: Timeout in milliseconds (converted to seconds for Selenium).
    """
    
    timeout_sec = 30  # default
    
    options = uc.ChromeOptions()
    # Critical flags for running in Docker/Render environment
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-setuid-sandbox")
    
    # Use a temp profile to avoid permission issues in Docker
    import tempfile
    import shutil
    user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    # Force remote debugging port to ensure driver can attach
    options.add_argument("--remote-debugging-port=9222")
    
    # Memory optimization flags for low-resource containers (512MB)
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dbus")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    # Tries to save memory by sharing process (can be unstable but useful for tight ram)
    # options.add_argument("--single-process") # Often causes more crashes in modern Chrome, kept commented.
    # options.add_argument("--no-zygote") # Similar to single-process, can cause instability.
    options.add_argument("--blink-settings=imagesEnabled=false") # Disable images to save RAM and bandwidth
    options.page_load_strategy = 'eager' # Don't wait for full page load (stylesheets/images)

    
    # If explicit headless requested AND we are not relying on Xvfb for 'headful',
    # we can add the argument. But usually for stealth, headful in Xvfb is best.
    # The caller (bot/runner) usually passes headless=True/False. 
    # If running in Docker with Xvfb, we ignore 'headless=True' logic here 
    # effectively running "visible" inside the fake screen.
    
    # However, if the user explicitly wants headless (e.g. local without Xvfb), 
    # we can support it. But for UC, 'headless' is a constructor arg usually.
    
    # We will instantiate with headless=False to maximize stealth, relying on Xvfb 
    # in production. If running locally without Xvfb, it will pop up.
    
    print(f"Launching Chrome (Headless arg ignored, relying on env/Xvfb)...")
    
    try:
        driver = uc.Chrome(options=options, headless=False, use_subprocess=True)
        driver.set_page_load_timeout(20) # Fail fast if page hangs
        driver.set_script_timeout(20)
    except Exception as e:
        print(f"Failed to start driver: {e}")
        return ""

    try:
        # driver.set_page_load_timeout(60) # Moved to init
        
        print(f"Navigating to coursebook...")
        driver.get("https://coursebook.utdallas.edu/search")
        
        # Wait for search box using explicit wait
        wait = WebDriverWait(driver, 15)
        search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SEARCH_SELECTOR)))
        
        # Human-like interaction
        time.sleep(random.uniform(1.0, 3.0))
        search_box.click()
        time.sleep(random.uniform(0.2, 0.5))
        
        # Type content
        for char in subject_number:
            search_box.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
            
        time.sleep(random.uniform(0.5, 1.0))
        search_box.send_keys("\n") # Enter
        
        # Buffer for results
        print("Waiting for results...")
        try:
             # Wait for at least one row
             WebDriverWait(driver, 20).until(
                 EC.presence_of_element_located((By.CSS_SELECTOR, RESULT_ROW_SELECTOR))
             )
        except Exception:
             print("Timeout waiting for results row. Retrying Enter...")
             actions = driver.find_element(By.CSS_SELECTOR, "body")
             actions.send_keys("\n")
             WebDriverWait(driver, 20).until(
                 EC.presence_of_element_located((By.CSS_SELECTOR, RESULT_ROW_SELECTOR))
             )

        # Allow hydration
        time.sleep(2)
        
        html = driver.page_source
        
        # Save debug screenshot (can be served by bot)
        driver.save_screenshot("debug_last_run.png")
        
        return html

    except Exception as e:
        print(f"Scrape error for {subject_number}: {e}")
        try:
            driver.save_screenshot("debug_last_run.png")
        except:
            pass
        return ""
    finally:
        try:
            driver.quit()
        except:
            pass
        try:
            import shutil
            shutil.rmtree(user_data_dir, ignore_errors=True)
        except:
            pass

def main(argv):
    if len(argv) != 4:
        print("Usage: python -m src.checker_uc SUBJECT NUMBER SECTION")
        print("Example: python -m src.checker_uc CS 4349 003")
        return

    subject = argv[1].upper()
    number = argv[2]
    section = argv[3].zfill(3)
    query = f"{subject} {number}"
    target_label = f"{subject} {number}.{section}"

    print(f"Searching for: {query}")
    html = fetch_results_html(query)
    
    if not html:
        print("No HTML returned.")
        return

    rows = parser.parse_results_fragment(html, row_selector=RESULT_ROW_SELECTOR)
    print(f"Parsed {len(rows)} rows")

    match = None
    for info in rows:
        print(f"{info.get('label')} - {info.get('status_text')}")
        if info.get("label") and info["label"].startswith(target_label):
            match = info
            break

    if not match:
        print("Target section not found.")
        return

    print("\nMATCH:", match)

if __name__ == "__main__":
    main(sys.argv)
