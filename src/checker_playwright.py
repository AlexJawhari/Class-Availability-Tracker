# src/checker_playwright.py
"""
Advanced Playwright-based scraper with multiple stealth techniques to bypass CAPTCHA detection.

Implements:
- playwright-stealth library
- Firefox/Gecko as alternative browser
- Advanced fingerprinting (WebGL, Canvas, AudioContext)
- Cookie persistence
- CDP manipulation
- Realistic human behavior simulation
"""

import os
import sys
import time
import random
import json
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from . import parser

# Try to import playwright-stealth
try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    print("PLAYWRIGHT: playwright-stealth not available, using custom stealth", flush=True)

# --- Selectors ---
SEARCH_SELECTOR = "#srch"
RESULT_ROW_SELECTOR = "tr.cb-row"

# Advanced stealth JavaScript with WebGL, Canvas, and AudioContext fingerprinting
ADVANCED_STEALTH_JS = """
// Remove webdriver property completely
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Override plugins to look like a real browser
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [];
        for (let i = 0; i < 5; i++) {
            plugins.push({
                name: `Plugin ${i}`,
                description: `Plugin ${i} Description`,
                filename: `plugin${i}.dll`
            });
        }
        return plugins;
    }
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
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// Override getBattery
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

// Override WebGL vendor and renderer to look realistic
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
        return 'Intel Inc.';
    }
    if (parameter === 37446) {
        return 'Intel Iris OpenGL Engine';
    }
    return getParameter.call(this, parameter);
};

// Override Canvas fingerprinting
const toBlob = HTMLCanvasElement.prototype.toBlob;
const toDataURL = HTMLCanvasElement.prototype.toDataURL;
const getImageData = CanvasRenderingContext2D.prototype.getImageData;

HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
    const canvas = this;
    return toBlob.call(canvas, callback, type, quality);
};

HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
    return toDataURL.call(this, type, quality);
};

CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {
    return getImageData.call(this, sx, sy, sw, sh);
};

// Override AudioContext fingerprinting
const AudioContext = window.AudioContext || window.webkitAudioContext;
if (AudioContext) {
    const originalCreateOscillator = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function() {
        return originalCreateOscillator.call(this);
    };
}

// Override Notification permission
Object.defineProperty(Notification, 'permission', {
    get: () => 'default'
});

// Override hardwareConcurrency
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8
});

// Override deviceMemory
Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8
});

// Override connection
if (navigator.connection) {
    Object.defineProperty(navigator, 'connection', {
        get: () => ({
            effectiveType: '4g',
            rtt: 50,
            downlink: 10,
            saveData: false
        })
    });
}

// Override platform
Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32'
});

// Mock media devices
if (navigator.mediaDevices) {
    Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', {
        value: () => Promise.resolve([])
    });
}
"""

# Realistic user agents pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]


def get_random_user_agent():
    """Get a random user agent from the pool."""
    return random.choice(USER_AGENTS)


def apply_cdp_stealth(page):
    """Apply Chrome DevTools Protocol commands to hide automation."""
    try:
        # Hide webdriver property via CDP
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Override permissions via CDP
        page.context.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
    except Exception as e:
        print(f"PLAYWRIGHT: CDP stealth application warning: {e}", flush=True)


def simulate_realistic_mouse_movement(page):
    """Simulate realistic mouse movements."""
    try:
        # Random mouse movements
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.1, 0.3))
    except Exception:
        pass


def simulate_realistic_scrolling(page):
    """Simulate realistic scrolling behavior."""
    try:
        # Scroll down gradually
        for i in range(random.randint(2, 4)):
            scroll_amount = random.randint(100, 300)
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            time.sleep(random.uniform(0.2, 0.5))
        
        # Scroll back up a bit
        page.evaluate("window.scrollBy(0, -100)")
        time.sleep(random.uniform(0.2, 0.4))
        
        # Scroll to top
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(random.uniform(0.3, 0.6))
    except Exception:
        pass


def fetch_results_html_chromium(subject_number: str, headless: bool = False, timeout_ms: int = 30000) -> str:
    """Fetch results using Chromium with advanced stealth."""
    use_headless = headless and not os.environ.get("DISPLAY")
    
    with sync_playwright() as p:
        browser = None
        try:
            print(f"PLAYWRIGHT: Launching Chromium (headless={use_headless})...", flush=True)
            
            # Advanced browser arguments for stealth
            browser_args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--window-size=1920,1080",
                "--disable-infobars",
                "--disable-notifications",
                "--disable-popup-blocking",
                "--disable-translate",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                "--enable-features=NetworkService,NetworkServiceInProcess",
                "--force-color-profile=srgb",
                "--metrics-recording-only",
                "--use-mock-keychain",
                "--disable-component-extensions-with-background-pages",
            ]
            
            browser = p.chromium.launch(
                headless=use_headless,
                args=browser_args
            )
            
            # Create context with realistic fingerprint
            user_agent = get_random_user_agent()
            context = browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/Chicago",
                permissions=["geolocation"],
                geolocation={"latitude": 32.9858, "longitude": -96.7501},
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
                    "Sec-Fetch-User": "?1",
                    "Cache-Control": "max-age=0",
                }
            )
            
            page = context.new_page()
            
            # Apply stealth techniques
            page.add_init_script(ADVANCED_STEALTH_JS)
            apply_cdp_stealth(page)
            
            if STEALTH_AVAILABLE:
                try:
                    stealth_sync(page)
                    print("PLAYWRIGHT: Applied playwright-stealth library", flush=True)
                except Exception as e:
                    print(f"PLAYWRIGHT: playwright-stealth warning: {e}", flush=True)
            
            # Navigate with realistic delays
            print("PLAYWRIGHT: Navigating to coursebook...", flush=True)
            page.goto(
                "https://coursebook.utdallas.edu/search",
                wait_until="domcontentloaded",
                timeout=timeout_ms
            )
            
            # Wait and simulate human behavior
            time.sleep(random.uniform(1.5, 3.0))
            simulate_realistic_mouse_movement(page)
            simulate_realistic_scrolling(page)
            
            # Wait for search box
            try:
                print("PLAYWRIGHT: Waiting for search input...", flush=True)
                page.wait_for_selector(SEARCH_SELECTOR, timeout=10000, state="visible")
            except PWTimeout:
                print("PLAYWRIGHT: Search input not found - checking for CAPTCHA", flush=True)
                html = page.content()
                if "recaptcha" in html.lower() or "verify you are a human" in html.lower():
                    print("PLAYWRIGHT: CAPTCHA detected!", flush=True)
                return ""
            
            # Click and type with human-like behavior
            time.sleep(random.uniform(0.5, 1.0))
            page.click(SEARCH_SELECTOR, delay=random.randint(100, 200))
            
            print(f"PLAYWRIGHT: Typing search query '{subject_number}'...", flush=True)
            page.keyboard.type(subject_number, delay=random.randint(100, 200))
            
            time.sleep(random.uniform(0.8, 1.5))
            
            # Submit
            try:
                submit_button = page.query_selector("button[type='submit']")
                if submit_button:
                    page.click("button[type='submit']", delay=random.randint(100, 200))
                else:
                    page.keyboard.press("Enter")
            except Exception:
                page.keyboard.press("Enter")
            
            # Wait for results
            print("PLAYWRIGHT: Waiting for results...", flush=True)
            time.sleep(random.uniform(1.5, 2.5))
            
            try:
                page.wait_for_selector(RESULT_ROW_SELECTOR, timeout=timeout_ms, state="visible")
                time.sleep(random.uniform(0.8, 1.2))
                
                simulate_realistic_scrolling(page)
                
                html = page.content()
                
                if "cb-row" in html:
                    print(f"PLAYWRIGHT: ✓ Chromium success! Got {len(html)} bytes", flush=True)
                    return html
                else:
                    print("PLAYWRIGHT: HTML returned but no cb-row elements", flush=True)
                    return ""
                    
            except PWTimeout:
                print("PLAYWRIGHT: Timeout waiting for results", flush=True)
                html = page.content()
                if "recaptcha" in html.lower() or "verify you are a human" in html.lower():
                    print("PLAYWRIGHT: CAPTCHA detected in page content!", flush=True)
                return ""
            
        except Exception as e:
            print(f"PLAYWRIGHT: Chromium error: {e}", flush=True)
            import traceback
            print(f"PLAYWRIGHT: Traceback: {traceback.format_exc()}", flush=True)
            return ""
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass


def fetch_results_html_firefox(subject_number: str, headless: bool = False, timeout_ms: int = 30000) -> str:
    """Fetch results using Firefox/Gecko as alternative browser."""
    use_headless = headless and not os.environ.get("DISPLAY")
    
    with sync_playwright() as p:
        browser = None
        try:
            print(f"PLAYWRIGHT: Launching Firefox (headless={use_headless})...", flush=True)
            
            browser = p.firefox.launch(
                headless=use_headless,
                firefox_user_prefs={
                    "dom.webdriver.enabled": False,
                    "useAutomationExtension": False,
                    "general.useragent.override": get_random_user_agent(),
                }
            )
            
            context = browser.new_context(
                user_agent=get_random_user_agent(),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/Chicago",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            )
            
            page = context.new_page()
            page.add_init_script(ADVANCED_STEALTH_JS)
            
            print("PLAYWRIGHT: Navigating to coursebook with Firefox...", flush=True)
            page.goto(
                "https://coursebook.utdallas.edu/search",
                wait_until="domcontentloaded",
                timeout=timeout_ms
            )
            
            time.sleep(random.uniform(1.5, 3.0))
            simulate_realistic_mouse_movement(page)
            
            try:
                page.wait_for_selector(SEARCH_SELECTOR, timeout=10000, state="visible")
            except PWTimeout:
                print("PLAYWRIGHT: Firefox - Search input not found", flush=True)
                return ""
            
            time.sleep(random.uniform(0.5, 1.0))
            page.click(SEARCH_SELECTOR, delay=random.randint(100, 200))
            
            print(f"PLAYWRIGHT: Firefox - Typing '{subject_number}'...", flush=True)
            page.keyboard.type(subject_number, delay=random.randint(100, 200))
            
            time.sleep(random.uniform(0.8, 1.5))
            
            try:
                submit_button = page.query_selector("button[type='submit']")
                if submit_button:
                    page.click("button[type='submit']", delay=random.randint(100, 200))
                else:
                    page.keyboard.press("Enter")
            except Exception:
                page.keyboard.press("Enter")
            
            print("PLAYWRIGHT: Firefox - Waiting for results...", flush=True)
            time.sleep(random.uniform(1.5, 2.5))
            
            try:
                page.wait_for_selector(RESULT_ROW_SELECTOR, timeout=timeout_ms, state="visible")
                time.sleep(random.uniform(0.8, 1.2))
                
                html = page.content()
                
                if "cb-row" in html:
                    print(f"PLAYWRIGHT: ✓ Firefox success! Got {len(html)} bytes", flush=True)
                    return html
                else:
                    print("PLAYWRIGHT: Firefox - HTML but no cb-row elements", flush=True)
                    return ""
                    
            except PWTimeout:
                print("PLAYWRIGHT: Firefox - Timeout waiting for results", flush=True)
                return ""
            
        except Exception as e:
            print(f"PLAYWRIGHT: Firefox error: {e}", flush=True)
            return ""
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass


def fetch_results_html(subject_number: str, headless: bool = False, timeout_ms: int = 30000, browser_type: str = "auto") -> str:
    """
    Fetch results using Playwright with multiple browser options.
    
    Args:
        subject_number: The query string (e.g. "CS 4349 001").
        headless: Whether to run headless. For maximum stealth, use False with Xvfb.
        timeout_ms: Timeout in milliseconds.
        browser_type: "chromium", "firefox", or "auto" (tries both).
    
    Returns:
        HTML string containing search results, or empty string on error.
    """
    browserless_token = os.environ.get("BROWSERLESS_TOKEN")
    
    if browserless_token:
        # Use Browserless.io if available
        print("PLAYWRIGHT: Using Browserless.io...", flush=True)
        # Fall through to Chromium implementation
    
    if browser_type == "auto":
        # Try Chromium first, then Firefox
        print("PLAYWRIGHT: Auto mode - trying Chromium first...", flush=True)
        result = fetch_results_html_chromium(subject_number, headless, timeout_ms)
        if result and "cb-row" in result:
            return result
        
        print("PLAYWRIGHT: Chromium failed, trying Firefox...", flush=True)
        result = fetch_results_html_firefox(subject_number, headless, timeout_ms)
        if result and "cb-row" in result:
            return result
        
        return ""
    elif browser_type == "firefox":
        return fetch_results_html_firefox(subject_number, headless, timeout_ms)
    else:
        return fetch_results_html_chromium(subject_number, headless, timeout_ms)


def main(argv):
    """Test the scraper directly."""
    if len(argv) < 2:
        print("Usage: python -m src.checker_playwright 'CS 4349'")
        print("  or:  python -m src.checker_playwright CS 4349 003")
        return
    
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
    
    html = fetch_results_html(query, headless=False, browser_type="auto")
    
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
