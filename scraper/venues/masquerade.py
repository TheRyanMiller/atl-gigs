import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from scraper import config
from scraper.utils.dates import normalize_time

MASQUERADE_BASE = "https://www.masqueradeatlanta.com"
MASQUERADE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Masquerade stages (events at other venues should be filtered out)
MASQUERADE_STAGES = ["Heaven", "Hell", "Purgatory", "Altar"]


def scrape_masquerade():
    """
    Scrape events from The Masquerade using HTML parsing.
    Only includes events at Masquerade stages (Heaven, Hell, Purgatory, Altar).
    """
    url = MASQUERADE_BASE + "/events/"
    try:
        resp = requests.get(url, headers=MASQUERADE_HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"    The Masquerade: ERROR - {e}")
        return []

    events = []

    for article in soup.select("article.event"):
        # Check if this is at The Masquerade (not an external venue)
        venue_span = article.select_one(".js-listVenue")
        if not venue_span:
            continue

        venue_text = venue_span.get_text(strip=True)
        stage = None
        for s in MASQUERADE_STAGES:
            if s in venue_text:
                stage = s
                break

        # Skip events not at Masquerade
        if not stage:
            continue

        # Parse date from .eventStartDate content attribute or spans
        date_el = article.select_one(".eventStartDate")
        if not date_el:
            continue

        # Try content attribute first (has full datetime)
        date_content = date_el.get("content", "")
        event_date = None
        doors_time = None

        if date_content:
            # Format: "November 30, 2025 6:00 pm"
            try:
                dt_obj = datetime.strptime(date_content, "%B %d, %Y %I:%M %p")
                event_date = dt_obj.strftime("%Y-%m-%d")
                doors_time = dt_obj.strftime("%H:%M")
            except ValueError:
                pass

        # Fallback to spans if content attribute didn't work
        if not event_date:
            month_el = date_el.select_one(".eventStartDate__month")
            day_el = date_el.select_one(".eventStartDate__date")
            year_el = date_el.select_one(".eventStartDate__year")

            if month_el and day_el and year_el:
                try:
                    date_str = f"{month_el.get_text(strip=True)} {day_el.get_text(strip=True)}, {year_el.get_text(strip=True)}"
                    dt_obj = datetime.strptime(date_str, "%b %d, %Y")
                    event_date = dt_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            else:
                continue

        # Parse doors time from .time-show if not already extracted
        if not doors_time:
            time_el = article.select_one(".time-show")
            if time_el:
                time_text = time_el.get_text(strip=True)
                # Extract time from "Doors 7:00 pm / All Ages"
                time_match = re.search(r"(\d{1,2}:\d{2})\s*(am|pm)", time_text, re.IGNORECASE)
                if time_match:
                    doors_time = normalize_time(f"{time_match.group(1)}{time_match.group(2)}")

        # Get title (headliner)
        title_el = article.select_one(".eventHeader__title")
        if not title_el:
            continue
        headliner = title_el.get_text(strip=True)
        if not headliner:
            continue

        # Get supporting acts
        support_el = article.select_one(".eventHeader__support")
        support_text = support_el.get_text(strip=True) if support_el else ""

        # Build artists list
        artists = [{"name": headliner}]
        if support_text:
            # Split by common delimiters: ", ", " & ", " and "
            support_acts = re.split(r",\s*|\s+&\s+|\s+and\s+", support_text)
            for act in support_acts:
                act = act.strip()
                if act and act != headliner:
                    artists.append({"name": act})

        # Get ticket URL
        ticket_link = article.select_one("a.btn-purple, a[itemprop='url']")
        ticket_url = ticket_link.get("href", "") if ticket_link else None

        if not ticket_url:
            # Try detail page link as fallback
            detail_link = article.select_one("a.wrapperLink")
            ticket_url = detail_link.get("href", "") if detail_link else None

        if not ticket_url:
            continue

        # Get detail URL
        detail_link = article.select_one("a.wrapperLink, a[href*='/events/']")
        detail_url = detail_link.get("href", "") if detail_link else None
        if detail_url and not detail_url.startswith("http"):
            detail_url = MASQUERADE_BASE + detail_url

        # Get image URL from background-image style
        image_el = article.select_one(".event--featuredImage")
        image_url = None
        if image_el:
            style = image_el.get("style", "")
            img_match = re.search(r"url\(['\"]?([^'\"]+)['\"]?\)", style)
            if img_match:
                image_url = img_match.group(1)

        events.append({
            "venue": "The Masquerade",
            "date": event_date,
            "doors_time": doors_time,
            "show_time": None,  # Site only shows doors time
            "artists": artists,
            "ticket_url": ticket_url,
            "info_url": detail_url,
            "image_url": image_url,
            "category": config.DEFAULT_CATEGORY,
            "stage": stage,  # Heaven, Hell, Purgatory, or Altar
        })

    return events
