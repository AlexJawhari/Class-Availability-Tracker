# src/checker_http.py
"""
Lightweight HTTP-based scraper for UTD Coursebook.
Uses direct HTTP requests instead of Selenium/Chrome.

Memory usage: ~10-20MB vs 300-500MB for Chrome/Xvfb
"""

import requests
from typing import Optional

# --- Constants ---
URL_HOME = "https://coursebook.utdallas.edu/search"
URL_AJAX = "https://coursebook.utdallas.edu/clips/clip-cb11-hat.zog"

# Current term format: <two-digit year><semester letter>
# Spring 2026 = 26s, Fall 2025 = 25f, Summer 2025 = 25u
CURRENT_TERM = "term_26s"  # Update this as semesters change

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://coursebook.utdallas.edu",
    "Referer": "https://coursebook.utdallas.edu/search",
}


def fetch_results_html(subject_number: str, headless: bool = True, timeout_ms: int = 30000) -> str:
    """
    Fetches the HTML fragment of search results using direct HTTP requests.
    
    Args:
        subject_number: The query string (e.g. "CS 4349" or "CS 4349 001").
        headless: Ignored (kept for API compatibility with checker_uc).
        timeout_ms: Ignored (kept for API compatibility).
    
    Returns:
        HTML string containing the search results table, or empty string on error.
    """
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Step 1: GET the homepage to establish cookies/session
        print("Fetching coursebook session...")
        resp_home = session.get(URL_HOME, timeout=15)
        if resp_home.status_code != 200:
            print(f"Failed to load homepage: {resp_home.status_code}")
            return ""
        
        # Step 2: POST to the AJAX endpoint
        # The API expects multiple s[] parameters for query and term
        print(f"Searching for: {subject_number}")
        data = [
            ("action", "search"),
            ("s[]", subject_number),
            ("s[]", CURRENT_TERM),
        ]
        
        resp_ajax = session.post(URL_AJAX, data=data, timeout=20)
        
        if resp_ajax.status_code != 200:
            print(f"AJAX request failed: {resp_ajax.status_code}")
            return ""
        
        # Step 3: Parse JSON response
        try:
            json_data = resp_ajax.json()
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            print(f"Response preview: {resp_ajax.text[:200]}")
            return ""
        
        # The HTML is in sethtml['#sr']
        sethtml = json_data.get("sethtml", {})
        results_html = sethtml.get("#sr", "")
        
        if not results_html:
            # Try alternate key
            results_html = sethtml.get("#searchresults", "")
        
        if results_html:
            print(f"Got {len(results_html)} bytes of results HTML")
        else:
            print("No results HTML found in response")
            print(f"Available keys: {list(sethtml.keys())}")
        
        return results_html
        
    except requests.exceptions.Timeout:
        print("Request timed out")
        return ""
    except requests.exceptions.RequestException as e:
        print(f"HTTP error: {e}")
        return ""
    except Exception as e:
        print(f"Unexpected error: {e}")
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
