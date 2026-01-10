# src/checker_tls.py
"""
Lightweight scraper using curl_cffi to bypass TLS fingerprinting.
Replaces the heavy Playwright implementation.
"""
from curl_cffi import requests
from . import parser

def fetch_results_html(query: str, headless: bool = True) -> str:
    """
    Fetches coursebook HTML using TLS Masquerading with Session priming.
    Args:
        query: e.g. "CS 4349 001"
    """
    # Clean up query: CS 4349 001 -> cs4349.001 (Standard UTD format)
    parts = query.split()
    if len(parts) >= 2:
        # standard: CS 4349 001 -> cs4349.001
        clean_q = f"{parts[0]}{parts[1]}"
        if len(parts) > 2:
             clean_q += f".{parts[2]}"
    else:
        clean_q = query.strip().replace(" ", "")
        
    print(f"TLS_SCRAPE: Fetching '{clean_q}' (Priming Session)...", flush=True)

    try:
        # Impersonate Chrome 120
        session = requests.Session(impersonate="chrome120")
        
        # 1. Prime the session (Get Cookies/Tokens)
        # Using a realistic header set
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Visit Home first
        home_resp = session.get("https://coursebook.utdallas.edu/", headers=headers, timeout=10)
        print(f"TLS_SCRAPE: Home Status {home_resp.status_code}", flush=True)
        
        # 2. Perform Search
        # Try the direct course URL first as it's cleaner: coursebook/cs4349.001
        # If that fails (404), fallback to search search path
        target_url = f"https://coursebook.utdallas.edu/{clean_q.lower()}"
        
        # Update Referer
        headers["Referer"] = "https://coursebook.utdallas.edu/"
        
        print(f"TLS_SCRAPE: Visiting {target_url}...", flush=True)
        response = session.get(target_url, headers=headers, timeout=20)
        
        print(f"TLS_SCRAPE: Status {response.status_code}, Size {len(response.text)} bytes", flush=True)
        
        if response.status_code == 200:
             # UTD returns 200 even for blocks sometimes, need to check content
             text = response.text.lower()
             if "recaptcha" in text or "verify you are a human" in text:
                 print("TLS_SCRAPE: Detected CAPTCHA/Block content!", flush=True)
                 return ""
             return response.text
             
        # Fallback to general search if specific URL fails
        print(f"TLS_SCRAPE: Direct link failed, trying search endpoint...", flush=True)
        search_url = f"https://coursebook.utdallas.edu/search/search={clean_q.lower()}"
        response = session.get(search_url, headers=headers, timeout=20)
        
        if response.status_code == 200:
             return response.text
             
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
