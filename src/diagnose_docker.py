
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

def test_standard_selenium(binary_path):
    print("\n--- Testing Standard Selenium ---")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        
        opts = Options()
        opts.binary_location = binary_path
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--headless=new") 
        opts.add_argument("--disable-gpu")
        
        # We assume chromedriver is in path or we need to install it?
        # UC manages driver, but standard selenium needs one. 
        # In this environment, we might verify if UC's patcher can download it.
        print("Attempting to launch standard Selenium (requires compatible chromedriver in PATH)...")
        # Just checking if we can even initialize options logic without crashing
        driver = webdriver.Chrome(options=opts)
        driver.get("https://google.com")
        print("Standard Selenium: SUCCESS (Page accessed)")
        driver.quit()
        return True
    except Exception as e:
        print(f"Standard Selenium Failed: {e}")
        # traceback.print_exc()
        return False

def test_uc(binary_path):
    print("\n--- Testing Undetected-Chromedriver ---")
    try:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.binary_location = binary_path
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Explicitly set headless=False as we rely on Xvfb
        # But for test, maybe try both?
        print("Initializing UC Chrome...")
        driver = uc.Chrome(options=options, headless=False, use_subprocess=True, version_main=None) # Auto version
        driver.get("https://coursebook.utdallas.edu")
        print(f"UC Chrome: SUCCESS. Title: {driver.title}")
        driver.quit()
        return True
    except Exception as e:
        print(f"UC Chrome Failed: {e}")
        traceback.print_exc()
        return False

def main():
    print("Diagnostics Starting...")
    bin_path = get_chrome_path()
    
    if not bin_path:
        print("CRITICAL: Google Chrome binary NOT FOUND in common paths.")
        # Try `which`
        try:
            bin_path = subprocess.check_output(["which", "google-chrome"]).decode().strip()
            print(f"Found via `which`: {bin_path}")
        except:
            print("`which google-chrome` failed.")
            sys.exit(1)
            
    check_chrome_version(bin_path)
    
    # We skip standard selenium test if we don't know if chromedriver is present manually, 
    # but UC handles driver download.
    
    uc_success = test_uc(bin_path)
    
    if uc_success:
        print("\nDiagnostics: UC seems working.")
    else:
        print("\nDiagnostics: UC Failed. See logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
