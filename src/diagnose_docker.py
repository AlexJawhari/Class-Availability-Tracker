
import sys
import os
import shutil
import subprocess
import traceback

def get_chrome_path():
    # Common paths for Google Chrome in Linux/Docker
    paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser"
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def check_chrome_version(binary_path):
    try:
        ver = subprocess.check_output([binary_path, "--version"]).decode().strip()
        print(f"Chrome Binary: {binary_path}")
        print(f"Chrome Version: {ver}")
        return ver
    except Exception as e:
        print(f"Error getting version: {e}")
        return None

def test_standard_selenium(binary_path, headless_mode=True):
    mode_str = "HEADLESS" if headless_mode else "HEADFUL"
    print(f"\n--- Testing Standard Selenium ({mode_str}) ---")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        import tempfile
        
        opts = Options()
        opts.binary_location = binary_path
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-setuid-sandbox")
        opts.add_argument("--remote-debugging-port=9222")
        
        user_data = tempfile.mkdtemp()
        opts.add_argument(f"--user-data-dir={user_data}")
        
        if headless_mode:
            opts.add_argument("--headless=new")
        
        print(f"Launching Selenium {mode_str}...")
        driver = webdriver.Chrome(options=opts)
        driver.get("https://google.com")
        print(f"Standard Selenium ({mode_str}): SUCCESS. Title: {driver.title}")
        driver.quit()
        return True
    except Exception as e:
        print(f"Standard Selenium ({mode_str}) Failed: {e}")
        # traceback.print_exc()
        return False

def test_uc(binary_path):
    print("\n--- Testing Undetected-Chromedriver ---")
    try:
        import undetected_chromedriver as uc
        import tempfile
        import shutil
        
        options = uc.ChromeOptions()
        options.binary_location = binary_path
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-setuid-sandbox")
        
        user_data = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={user_data}")
        options.add_argument("--remote-debugging-port=9222")
        
        print("Initializing UC Chrome...")
        # UC needs version_main sometimes if auto-detection fails or is mismatching
        # But we'll try default first.
        driver = uc.Chrome(options=options, headless=False, use_subprocess=True)
        driver.get("https://coursebook.utdallas.edu")
        print(f"UC Chrome: SUCCESS. Title: {driver.title}")
        driver.quit()
        try:
            shutil.rmtree(user_data)
        except:
            pass
        return True
    except Exception as e:
        print(f"UC Chrome Failed: {e}")
        traceback.print_exc()
        return False

def main():
    print("Diagnostics Starting...")
    print(f"DISPLAY env var: {os.environ.get('DISPLAY', 'NOT SET')}")
    
    bin_path = get_chrome_path()
    
    if not bin_path:
        print("CRITICAL: Google Chrome binary NOT FOUND.")
        try:
            bin_path = subprocess.check_output(["which", "google-chrome"]).decode().strip()
            print(f"Found via `which`: {bin_path}")
        except:
            sys.exit(1)
            
    ver = check_chrome_version(bin_path)
    
    # We skip standard selenium tests to conserve memory on startup, 
    # as we suspect OOM is the culprit. We jump straight to the library we use.
    
    # 3. Test UC (Library check)
    uc_success = test_uc(bin_path)
    
    if uc_success:
        print("\nDiagnostics: UC seems working.")
    else:
        print("\nDiagnostics: UC Failed.")

if __name__ == "__main__":
    main()
