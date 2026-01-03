import requests
from bs4 import BeautifulSoup
import urllib3

# Suppress insecure request warnings if we were verifying=False (we are not, but good practice)
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL_HOME = "https://coursebook.utdallas.edu/search"
URL_CLIP = "https://coursebook.utdallas.edu/clips/clip-cb11-hat.zog"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # "X-Requested-With": "XMLHttpRequest", # Only needed for the POST
}

def test_scrape():
    s = requests.Session()
    s.headers.update(HEADERS)

    # 1. GET the home page to get cookies and the token
    print(f"1. GET {URL_HOME}...")
    resp = s.get(URL_HOME)
    print(f"   Status: {resp.status_code}")
    
    # 2. Extract the token
    soup = BeautifulSoup(resp.text, 'lxml')
    # Use find to locate hidden input with name="token"
    # Subagent said: document.querySelector('input[name="token"]')
    token_input = soup.find("input", {"name": "token"})
    if not token_input:
        print("FAIL: Could not find 'token' input in HTML.")
        # print("HTML Preview:", resp.text[:1000])
        return
    
    token = token_input.get("value")
    print(f"   Token found: {token}")

    # 3. POST to the clip URL
    # Headers for the AJAX request - mimic Chrome fully
    s.headers.update({
        "X-Requested-With": "XMLHttpRequest",
        "Referer": URL_HOME,
        "Origin": "https://coursebook.utdallas.edu",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Te": "trailers",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache"
    })

    # Try adding token to the body
    data = {
        "action": "search",
        "s[]": ["CS 4349", "term_26s"],
        "token": token
    }
    
    print(f"2. POST to {URL_CLIP} with token={token[:10]}...")
    resp_post = s.post(URL_CLIP, data=data)
    print(f"   Status: {resp_post.status_code}")
    print(f"   Len: {len(resp_post.text)}")
    
    if "CS 4349" in resp_post.text:
        print("SUCCESS! Found class data.")
        if "cb-row" in resp_post.text:
             print("   'cb-row' found. Table is valid.")
    else:
        print("FAIL: Class data not found.")
        print("   Preview:", resp_post.text[:500])

if __name__ == "__main__":
    test_scrape()
