# src/checker_tls.py
"""
Lightweight scraper using curl_cffi to bypass TLS fingerprinting.
Replaces the heavy Playwright implementation.
"""
from curl_cffi import requests
from . import parser

def fetch_results_html(query: str, headless: bool = True) -> str:
    """
    Fetches coursebook HTML using TLS Masquerading.
    Args:
        query: e.g. "CS 4349 001"
        headless: Ignored, kept for compatibility.
    """
    print(f"TLS_SCRAPE: Fetching '{query}'...", flush=True)
    
    # Normalize query for URL if possible, or use search endpoint
    # Trying direct direct link structure: https://coursebook.utdallas.edu/cs4349.001term25s
    # But term is dynamic.
    # Safest is the search URI: https://coursebook.utdallas.edu/search/search={query}
    # Clean up query
    clean_q = query.strip().replace(" ", "") # CS4349001
    
    # If we have a section, we can try specific url, but let's try the general search path
    # which UTD uses: /search/search=query
    url = f"https://coursebook.utdallas.edu/search/search={clean_q}"
    
    try:
        # Impersonate Chrome 120 to bypass JA3/JA4 fingerprinting
        session = requests.Session(impersonate="chrome120")
        
        # Add basic headers just in case
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://coursebook.utdallas.edu/",
            "Upgrade-Insecure-Requests": "1"
        }
        
        response = session.get(url, headers=headers, timeout=20)
        
        print(f"TLS_SCRAPE: Status {response.status_code}, Size {len(response.text)} bytes", flush=True)
        
        if response.status_code == 200:
            # Check if we got a captcha or block (rare with curl_cffi but possible)
            if "recaptcha" in response.text.lower() or "please verify you are a human" in response.text.lower():
                print("TLS_SCRAPE: Detected CAPTCHA/Block content!", flush=True)
                return ""
            return response.text
        else:
            print(f"TLS_SCRAPE: Failed request {response.status_code}", flush=True)
            return ""
            
    except Exception as e:
        print(f"TLS_SCRAPE: Error {e}", flush=True)
        return ""

if __name__ == "__main__":
    # Test
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "CS 4349"
    html = fetch_results_html(q)
    print("Preview:", html[:200])
    rows = parser.parse_results_fragment(html)
    print(f"Parsed {len(rows)} rows.")
