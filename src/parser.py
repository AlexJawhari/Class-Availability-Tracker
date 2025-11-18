# src/parser.py
"""
Parsing helpers for Coursebook search results.

Functions:
- parse_results_fragment(html, row_selector="tr.cb-row") -> list[dict]
- is_section_open(info: dict) -> bool

Each returned dict has keys:
- label: string like "CS 4349.003" or None
- enrolled: int or None
- capacity: int or None
- seats_available: int or None (when page shows available seats)
- status_text: normalized lower-case status (e.g. "full", "open", "waitlist", or None)
- raw: raw text content for the row (for debugging)
"""

from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional

DEFAULT_ROW_SELECTOR = "tr.cb-row"

# Patterns to try (order matters)
# These pattern variables, utilize the regex library of python
# to basically look for a specified pattern within the data we process,
# the benefit to using this library, is once we've found a pattern
# we can run various commands on the found patterns, because the pattern
# is turned into an object.
# The various letters and slashes in the quotes simply denote
# the pattern match to look for either a number, letter, space, etc.
NUMERIC_SLASH_RE = re.compile(r"(\d+)\s*/\s*(\d+)")  # "12 / 30" or "12/30"
ENRL_CAP_RE = re.compile(r"Enrl[:\s]*?(\d+).*?Cap[:\s]*?(\d+)", re.IGNORECASE)  # "Enrl: 12 Cap: 30"
SEATS_AVAILABLE_RE = re.compile(r"(\d+)\s+(?:seats?|seats?\s+available)", re.IGNORECASE)  # "3 seats available"
# fallback: "Open" / "Full" / "Waitlist" / "Closed" words to check

def parse_row_element(tr) -> Dict:
    """Parse a BeautifulSoup <tr> element and return a dict of fields.
       BeautifulSoup is a library that allows for making a parse tree of html tags
       and data
    """
    # full visible text for the row, with single spaces between text nodes
    # so this line basically just gets all of the text from the table on the 
    # webpage, assigns it to the text var, and strips it of whitespace and 
    # leading/trailing chars
    # this is used for regex searches below as well
    text = tr.get_text(" ", strip=True)

    # label: usually in an <a> with class stopbubble inside first td
    # this block is looking for an anchor tag in the html, which is 
    # the tag that creates a hyperlink to some other page
    anchor_tag = tr.select_one("td a.stopbubble")
    if not anchor_tag:
        # fallback: any first anchor
        anchor_tag = tr.select_one("a")
    label = anchor_tag.get_text(strip=True) if anchor_tag else None

    # status span if present (site uses classes like section-open / section-closed)
    # checks for if the tr has span tags that contain the following options to 
    # see if the class is open or closed quickly
    # span often contains "full" or "open" explicitly so it is preferred when present
    status_span = tr.select_one("span.section-open, span.section-closed, span.section-waitlist")
    status_text = status_span.get_text(strip=True).lower() if status_span else None

    # numeric: try "12/30" or "12 / 30" first (most compact format)
    # here we are checking first if the slash match pattern finds the data
    # and if so we simply fill enrolled and capacity vars with the found pattern
    # else we check using the enroll pattern, if thats found then we 
    # fill the vars like before, if not we set the vars to none for now
    slash_match = NUMERIC_SLASH_RE.search(text)
    if slash_match:
        enrolled = int(slash_match.group(1))
        capacity = int(slash_match.group(2))
    else:
        # try "Enrl: 12 Cap: 30" format if the slash form wasn't found
        enrl_cap_match = ENRL_CAP_RE.search(text)
        if enrl_cap_match:
            enrolled = int(enrl_cap_match.group(1))
            capacity = int(enrl_cap_match.group(2))
        else:
            enrolled = None
            capacity = None

    # seats available (some rows mention "3 seats available")
    # basically doing the above pattern checks, except because this pattern
    # would directly provide us with any open seats
    # so we dont have to do various checks or if statements
    seats_match = SEATS_AVAILABLE_RE.search(text)
    seats_available = int(seats_match.group(1)) if seats_match else None

    # Normalize status words from raw text if status_span missing
    # Fills our status text if the html doesnt provide information
    # we can just parse the raw text 
    if not status_text:
        t = text.lower()
        if "full" in t:
            status_text = "full"
        elif "open" in t or "available" in t or "seats available" in t or "seat available" in t:
            status_text = "open"
        elif "waitlist" in t or "wait list" in t or "wl" in t:
            status_text = "waitlist"
        elif "closed" in t:
            status_text = "closed"
        else:
            status_text = None

    # returns the various vars from the data parsed so they can be displayed
    return {
        "label": label,
        "enrolled": enrolled,
        "capacity": capacity,
        "seats_available": seats_available,
        "status_text": status_text,
        "raw": text
    }

# "-> List[Dict]" is a type hint - basically just a comment letting us 
# know that the function returns a list where each element is a dict
def parse_results_fragment(html: str, row_selector: str = DEFAULT_ROW_SELECTOR) -> List[Dict]:
    """
    Given full HTML (rendered by Playwright), parse all rows and return a list of info dicts.
    """
    # creates soup object from html string, soup is the parsed DOM
    # then we do soup.select to get just the rows
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(row_selector)

    # we create the results list that will be returned
    results = []

    # for each parsh_row_element, the table row has the data extracted
    # and then added to the current info dict, which then gets 
    # appended to the results list
    for tr in rows:
        info = parse_row_element(tr)
        results.append(info)
    return results

def is_section_open(info: Dict) -> bool:
    """
    Decide whether the section is open.
    Priority:
      1) If seats_available is present -> seats_available > 0 means open.
      2) If enrolled & capacity present -> enrolled < capacity means open.
      3) If status_text indicates open/available -> open.
      4) Otherwise -> assume closed (safer default).
    """
    # 1) seats available explicit
    seats_available = info.get("seats_available")
    if seats_available is not None:
        return seats_available > 0

    # 2) numeric enrolled/capacity
    en = info.get("enrolled")
    cap = info.get("capacity")
    if en is not None and cap is not None:
        return en < cap

    # 3) textual status
    # uses generator expression (efficient list to return a t/f quickly)
    # basically just checks if the token in status, matches one of the strings
    # that we iterate over in the list of open avialable etc, and true if 
    # theres a match and false otherwise
    status = (info.get("status_text") or "").lower()
    if status:
        if any(token in status for token in ["open", "available", "seat"]):
            return True
        if any(token in status for token in ["full", "closed", "waitlist", "wait list", "wl"]):
            return False

    # 4) fallback: be conservative and treat as closed
    return False
