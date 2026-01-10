# src/scraper.py
"""
Scraper orchestrator with intelligent fallback chain.

Implements multiple scraping methods in order of preference:
1. Playwright with stealth techniques (primary - most reliable, bypasses CAPTCHA)
2. Token extraction method (checker_http.py) - Lightweight fallback
3. curl_cffi with TLS masquerading (checker_tls.py) - Last resort

This ensures maximum reliability by trying multiple approaches if one fails.
"""

import logging
from typing import Optional

# Import scrapers
try:
    from .checker_playwright import fetch_results_html as fetch_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("WARNING: checker_playwright not available", flush=True)

try:
    from .checker_http import fetch_results_html as fetch_http
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    print("WARNING: checker_http not available", flush=True)

try:
    from .checker_tls import fetch_results_html as fetch_tls
    TLS_AVAILABLE = True
except ImportError:
    TLS_AVAILABLE = False
    print("WARNING: checker_tls (curl_cffi) not available", flush=True)


def fetch_results_html(query: str, headless: bool = False, timeout_ms: int = 30000) -> str:
    """
    Fetch coursebook HTML using intelligent fallback chain.
    
    Args:
        query: Course query string (e.g. "CS 4349 001")
        headless: For Playwright, False uses headful mode (more stealthy). Ignored for other methods.
        timeout_ms: Timeout in milliseconds
    
    Returns:
        HTML string containing search results, or empty string if all methods fail
    
    The method used is logged to stdout for debugging.
    """
    methods_tried = []
    
    # Method 1: Playwright with stealth (primary - most reliable for bypassing CAPTCHA)
    # Try Chromium first, then Firefox if Chromium fails
    if PLAYWRIGHT_AVAILABLE:
        # Try Chromium
        try:
            print(f"SCRAPER: Trying Playwright Chromium stealth for '{query}'...", flush=True)
            html = fetch_playwright(query, headless=headless, timeout_ms=timeout_ms, browser_type="chromium")
            if html and "cb-row" in html:
                print(f"SCRAPER: ✓ Playwright Chromium succeeded!", flush=True)
                return html
            elif html:
                print(f"SCRAPER: Playwright Chromium returned HTML but no cb-row elements", flush=True)
                methods_tried.append("playwright_chromium(partial)")
            else:
                print(f"SCRAPER: Playwright Chromium returned empty result", flush=True)
                methods_tried.append("playwright_chromium(empty)")
        except Exception as e:
            print(f"SCRAPER: Playwright Chromium failed: {e}", flush=True)
            methods_tried.append(f"playwright_chromium(error: {str(e)[:50]})")
        
        # Try Firefox if Chromium failed
        try:
            print(f"SCRAPER: Trying Playwright Firefox stealth for '{query}'...", flush=True)
            html = fetch_playwright(query, headless=headless, timeout_ms=timeout_ms, browser_type="firefox")
            if html and "cb-row" in html:
                print(f"SCRAPER: ✓ Playwright Firefox succeeded!", flush=True)
                return html
            elif html:
                print(f"SCRAPER: Playwright Firefox returned HTML but no cb-row elements", flush=True)
                methods_tried.append("playwright_firefox(partial)")
            else:
                print(f"SCRAPER: Playwright Firefox returned empty result", flush=True)
                methods_tried.append("playwright_firefox(empty)")
        except Exception as e:
            print(f"SCRAPER: Playwright Firefox failed: {e}", flush=True)
            methods_tried.append(f"playwright_firefox(error: {str(e)[:50]})")
    else:
        methods_tried.append("playwright(unavailable)")
    
    # Method 2: Token extraction (lightweight fallback)
    if HTTP_AVAILABLE:
        try:
            print(f"SCRAPER: Trying token extraction method for '{query}'...", flush=True)
            html = fetch_http(query, headless=headless, timeout_ms=timeout_ms)
            if html and "cb-row" in html:
                print(f"SCRAPER: ✓ Token extraction method succeeded!", flush=True)
                return html
            elif html:
                print(f"SCRAPER: Token extraction returned HTML but no cb-row elements (might be CAPTCHA)", flush=True)
                methods_tried.append("token_extraction(partial)")
            else:
                print(f"SCRAPER: Token extraction returned empty result", flush=True)
                methods_tried.append("token_extraction(empty)")
        except Exception as e:
            print(f"SCRAPER: Token extraction method failed: {e}", flush=True)
            methods_tried.append(f"token_extraction(error: {str(e)[:50]})")
    else:
        methods_tried.append("token_extraction(unavailable)")
    
    # Method 3: curl_cffi with TLS masquerading (last resort)
    if TLS_AVAILABLE:
        try:
            print(f"SCRAPER: Trying curl_cffi TLS method for '{query}'...", flush=True)
            html = fetch_tls(query, headless=headless)
            if html and "cb-row" in html:
                print(f"SCRAPER: ✓ curl_cffi TLS method succeeded!", flush=True)
                return html
            elif html:
                print(f"SCRAPER: curl_cffi returned HTML but no cb-row elements (might be CAPTCHA)", flush=True)
                methods_tried.append("curl_cffi(partial)")
            else:
                print(f"SCRAPER: curl_cffi returned empty result", flush=True)
                methods_tried.append("curl_cffi(empty)")
        except Exception as e:
            print(f"SCRAPER: curl_cffi method failed: {e}", flush=True)
            methods_tried.append(f"curl_cffi(error: {str(e)[:50]})")
    else:
        methods_tried.append("curl_cffi(unavailable)")
    
    # All methods failed
    print(f"SCRAPER: ✗ All scraping methods failed for '{query}'", flush=True)
    print(f"SCRAPER: Methods tried: {', '.join(methods_tried)}", flush=True)
    print(f"SCRAPER: This likely indicates CAPTCHA/bot detection or network issues", flush=True)
    
    return ""


def get_available_methods() -> list:
    """
    Get list of available scraping methods.
    
    Returns:
        List of method names that are available
    """
    methods = []
    if PLAYWRIGHT_AVAILABLE:
        methods.append("playwright_chromium_stealth")
        methods.append("playwright_firefox_stealth")
    if HTTP_AVAILABLE:
        methods.append("token_extraction")
    if TLS_AVAILABLE:
        methods.append("curl_cffi_tls")
    return methods


if __name__ == "__main__":
    # Test the orchestrator
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "CS 4349"
    
    print(f"Testing scraper orchestrator for: {query}")
    print(f"Available methods: {get_available_methods()}")
    
    html = fetch_results_html(query, headless=False)
    
    if html:
        print(f"\n✓ Success! Got {len(html)} bytes of HTML")
        print(f"Preview: {html[:300]}...")
    else:
        print("\n✗ All methods failed")
