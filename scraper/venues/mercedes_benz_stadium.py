import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from scraper.utils.categories import detect_category_from_text, detect_category_from_ticket_url
from scraper.utils.dates import normalize_time

MERCEDES_BENZ_STADIUM_BASE = "https://www.mercedesbenzstadium.com"
MERCEDES_BENZ_STADIUM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MBS_CATEGORY_MAP = {
    "sports": "sports",
    "concert": "concerts",
    "other": "misc",
    "conference": "misc",
    "home depot backyard": "misc",
}


def scrape_mercedes_benz_stadium():
    url = MERCEDES_BENZ_STADIUM_BASE + "/events"
    try:
        resp = requests.get(url, headers=MERCEDES_BENZ_STADIUM_HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"    Mercedes-Benz Stadium: ERROR - {e}")
        return []

    events = []
    seen_urls = set()

    for card in soup.select("div.events--item.w-dyn-item"):
        title_el = card.select_one("h3")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue

        category_el = card.select_one("div.events_tags--item.w-dyn-item")
        raw_category = category_el.get_text(strip=True).lower() if category_el else "other"
        category = MBS_CATEGORY_MAP.get(raw_category, "misc")

        detail_items = card.select("div.events_feature_details_dt")
        date_str = detail_items[0].get_text(strip=True) if len(detail_items) > 0 else None
        time_str = detail_items[1].get_text(strip=True) if len(detail_items) > 1 else None

        event_date = None
        if date_str:
            for fmt in ["%B %d, %Y", "%B %Y"]:
                try:
                    dt_obj = datetime.strptime(date_str, fmt)
                    event_date = dt_obj.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

        if not event_date:
            continue

        show_time = None
        if time_str and time_str.upper() not in ["TBD", "TBA"]:
            time_match = re.search(r"(\d{1,2}:\d{2})\s*(AM|PM)", time_str, re.IGNORECASE)
            if time_match:
                show_time = normalize_time(f"{time_match.group(1)}{time_match.group(2)}")

        detail_link = card.select_one("a.btn--3[href*='/events/']")
        detail_url = None
        if detail_link:
            detail_url = detail_link.get("href", "")
            if detail_url and not detail_url.startswith("http"):
                detail_url = MERCEDES_BENZ_STADIUM_BASE + detail_url

        ticket_link = card.select_one("a.btn--1")
        ticket_url = ticket_link.get("href", "") if ticket_link else None
        if not ticket_url:
            ticket_url = detail_url
        if not ticket_url:
            continue

        key = detail_url or ticket_url
        if key in seen_urls:
            continue
        seen_urls.add(key)

        img = card.select_one("img.event_image")
        image_url = None
        if img:
            image_url = img.get("src") or img.get("data-src")
            if image_url and not image_url.startswith("http"):
                image_url = MERCEDES_BENZ_STADIUM_BASE + image_url

        final_category = category
        if category == "misc":
            detected = detect_category_from_text(title) or detect_category_from_ticket_url(ticket_url)
            if detected:
                final_category = detected

        events.append({
            "venue": "Mercedes-Benz Stadium",
            "date": event_date,
            "doors_time": None,
            "show_time": show_time,
            "artists": [{"name": title}],
            "ticket_url": ticket_url,
            "info_url": detail_url,
            "image_url": image_url,
            "category": final_category,
        })

    team_configs = [
        ("falcons", "Atlanta Falcons vs. ", "falcons"),
        ("united", "Atlanta United vs. ", "AU_Primary"),
    ]

    for team_class, title_prefix, logo_pattern in team_configs:
        team_item = soup.select_one(f"div.events_game--item.{team_class}")
        if not team_item:
            continue

        team_logo = None
        for img in team_item.select("img"):
            src = img.get("src", "")
            if logo_pattern in src:
                team_logo = src
                break

        text_content = team_item.get_text(separator=" | ", strip=True).replace("\xa0", " ")
        parts = [p.strip().replace("\xa0", " ") for p in text_content.split("|") if p.strip()]

        opponent = None
        for i, part in enumerate(parts):
            normalized = part.replace("\xa0", " ").upper()
            if "NEXT" in normalized and "HOME" in normalized:
                if i + 1 < len(parts):
                    opponent = parts[i + 1]
                    if "vs." in opponent:
                        opponent = opponent.split("vs.")[-1].strip()
                break

        if not opponent:
            continue

        team_date = None
        team_time = None
        for part in parts:
            for fmt in ["%B %d, %Y", "%b %d, %Y"]:
                try:
                    dt_obj = datetime.strptime(part, fmt)
                    team_date = dt_obj.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    pass
            time_match = re.match(r"(\d{1,2}:\d{2})\s*(am|pm)", part, re.IGNORECASE)
            if time_match:
                team_time = normalize_time(f"{time_match.group(1)}{time_match.group(2)}")

        if not team_date:
            continue

        title = f"{title_prefix}{opponent}"
        if any(e["date"] == team_date and title in e["artists"][0]["name"] for e in events):
            continue

        ticket_link = team_item.select_one("a[href*='ticketmaster'], a[href*='tickets']")
        team_ticket_url = ticket_link.get("href") if ticket_link else None

        events.append({
            "venue": "Mercedes-Benz Stadium",
            "date": team_date,
            "doors_time": None,
            "show_time": team_time,
            "artists": [{"name": title}],
            "ticket_url": team_ticket_url,
            "info_url": None,
            "image_url": team_logo,
            "category": "sports",
        })

    print(f"    Mercedes-Benz Stadium: {len(events)} events")
    return events
