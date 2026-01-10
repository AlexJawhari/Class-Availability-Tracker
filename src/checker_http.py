# src/checker_http.py
"""
Lightweight HTTP-based scraper for UTD Coursebook.
Uses direct HTTP requests instead of Selenium/Chrome.

Memory usage: ~10-20MB vs 300-500MB for Chrome/Xvfb
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional
import time

# --- Constants ---
URL_HOME = "https://coursebook.utdallas.edu/search"
URL_AJAX = "https://coursebook.utdallas.edu/clips/clip-cb11-hat.zog"

# Current term format: <two-digit year><semester letter>
# Spring 2026 = 26s, Fall 2025 = 25f, Summer 2025 = 25u
CURRENT_TERM = "term_26s"  # Update this as semesters change

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_results_html(subject_number: str, headless: bool = True, timeout_ms: int = 30000) -> str:
    """
    Fetches the HTML fragment of search results using token extraction method.
    This method mimics a real browser session by extracting CSRF token from the homepage.
    
    Args:
        subject_number: The query string (e.g. "CS 4349" or "CS 4349 001").
        headless: Ignored (kept for API compatibility).
        timeout_ms: Timeout in milliseconds (converted to seconds).
    
    Returns:
        HTML string containing the search results table, or empty string on error.
    """
    timeout_sec = min(timeout_ms / 1000.0, 30.0)  # Convert to seconds, cap at 30s
    
    try:
        session = requests.Session()
        session.headers.update(HEADERS_BASE)
        
        # Step 1: GET the homepage to establish cookies/session and extract token
        print("HTTP_SCRAPE: Fetching homepage to extract token...", flush=True)
        resp_home = session.get(URL_HOME, timeout=timeout_sec)
        
        if resp_home.status_code != 200:
            print(f"HTTP_SCRAPE: Failed to load homepage: {resp_home.status_code}", flush=True)
            return ""
        
        # Step 2: Extract CSRF token from HTML
        try:
            soup = BeautifulSoup(resp_home.text, 'lxml')
            token_input = soup.find("input", {"name": "token"})
            
            if not token_input:
                print("HTTP_SCRAPE: Could not find token input in HTML (CAPTCHA or page changed?)", flush=True)
                # Check for CAPTCHA indicators
                if "recaptcha" in resp_home.text.lower() or "verify you are a human" in resp_home.text.lower():
                    print("HTTP_SCRAPE: Detected CAPTCHA/Block content on homepage!", flush=True)
                return ""
            
            token = token_input.get("value")
            if not token:
                print("HTTP_SCRAPE: Token input found but has no value", flush=True)
                return ""
                
            print(f"HTTP_SCRAPE: Token extracted successfully (length: {len(token)})", flush=True)
        except Exception as e:
            print(f"HTTP_SCRAPE: Error parsing token from homepage: {e}", flush=True)
            return ""
        
        # Step 3: POST to AJAX endpoint with token and proper headers
        print(f"HTTP_SCRAPE: Searching for '{subject_number}'...", flush=True)
        
        # Update headers for AJAX request - mimic Chrome fully
        ajax_headers = {
            **HEADERS_BASE,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": URL_HOME,
            "Origin": "https://coursebook.utdallas.edu",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        
        # Prepare form data with token
        # The API expects: action=search, s[]=query, s[]=term, token=csrf_token
        data = {
            "action": "search",
            "s[]": [subject_number, CURRENT_TERM],
            "token": token
        }
        
        # Small delay to mimic human behavior
        time.sleep(0.5)
        
        resp_ajax = session.post(URL_AJAX, data=data, headers=ajax_headers, timeout=timeout_sec)
        
        if resp_ajax.status_code != 200:
            print(f"HTTP_SCRAPE: AJAX request failed: {resp_ajax.status_code}", flush=True)
            if resp_ajax.status_code == 403:
                print("HTTP_SCRAPE: 403 Forbidden - likely CAPTCHA/bot detection", flush=True)
            return ""
        
        # Step 4: Parse JSON response
        try:
            json_data = resp_ajax.json()
        except Exception as e:
            print(f"HTTP_SCRAPE: Failed to parse JSON: {e}", flush=True)
            print(f"HTTP_SCRAPE: Response preview: {resp_ajax.text[:500]}", flush=True)
            # Check for CAPTCHA in response
            if "recaptcha" in resp_ajax.text.lower() or "verify you are a human" in resp_ajax.text.lower():
                print("HTTP_SCRAPE: Detected CAPTCHA in response!", flush=True)
            return ""
        
        # Step 5: Extract HTML from JSON response
        # The HTML is in sethtml['#sr'] or sethtml['#searchresults']
        sethtml = json_data.get("sethtml", {})
        results_html = sethtml.get("#sr", "")
        
        if not results_html:
            # Try alternate key
            results_html = sethtml.get("#searchresults", "")
        
        if results_html:
            # Validate that we got actual course data
            if "cb-row" in results_html:
                print(f"HTTP_SCRAPE: Success! Got {len(results_html)} bytes of results HTML with cb-row elements", flush=True)
                return results_html
            else:
                print(f"HTTP_SCRAPE: Got HTML but no cb-row elements found (might be empty results or CAPTCHA)", flush=True)
                print(f"HTTP_SCRAPE: HTML preview: {results_html[:200]}", flush=True)
                return ""
        else:
            print("HTTP_SCRAPE: No results HTML found in response", flush=True)
            print(f"HTTP_SCRAPE: Available keys in sethtml: {list(sethtml.keys())}", flush=True)
            print(f"HTTP_SCRAPE: JSON keys: {list(json_data.keys())}", flush=True)
            return ""
        
    except requests.exceptions.Timeout:
        print("HTTP_SCRAPE: Request timed out", flush=True)
        return ""
    except requests.exceptions.RequestException as e:
        print(f"HTTP_SCRAPE: HTTP error: {e}", flush=True)
        return ""
    except Exception as e:
        print(f"HTTP_SCRAPE: Unexpected error: {e}", flush=True)
        import traceback
        print(f"HTTP_SCRAPE: Traceback: {traceback.format_exc()}", flush=True)
        return ""


def main():
    """Test the scraper directly."""
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "CS 4349"
    
    print(f"Testing HTTP scraper for: {query}")
    html = fetch_results_html(query)
    
    if html:
        print(f"\n--- Results ({len(html)} bytes) ---")
        # Show first 500 chars
        print(html[:500])
        
        if "cb-row" in html:
            print("\n✓ Found cb-row elements (valid table)")
        else:
            print("\n✗ No cb-row elements found")
    else:
        print("No results returned")


if __name__ == "__main__":
    main()
