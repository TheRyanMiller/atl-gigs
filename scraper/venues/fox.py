import json
import random
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

try:
    import cloudscraper  # type: ignore
except ImportError:
    cloudscraper = None

from scraper import config

FOX_THEATRE_BASE = "https://www.foxtheatre.org"
FOX_THEATRE_AJAX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.foxtheatre.org/events",
    "Origin": "https://www.foxtheatre.org",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def parse_fox_date_range(date_text):
    date_text = " ".join(date_text.split())
    date_text = date_text.replace(" - ", "-").replace("- ", "-").replace(" -", "-")

    month_map = {
        "january": "Jan", "february": "Feb", "march": "Mar", "april": "Apr",
        "may": "May", "june": "Jun", "july": "Jul", "august": "Aug",
        "september": "Sep", "october": "Oct", "november": "Nov", "december": "Dec",
    }
    for full, abbrev in month_map.items():
        date_text = re.sub(rf"\b{full}\b", abbrev, date_text, flags=re.IGNORECASE)

    single_match = re.match(r"^([A-Za-z]+)\s+(\d+),\s*(\d{4})$", date_text)
    if single_match:
        month_str, day, year = single_match.groups()
        try:
            date = datetime.strptime(f"{month_str} {day}, {year}", "%b %d, %Y")
            date_str = date.strftime("%Y-%m-%d")
            return date_str, date_str
        except ValueError:
            pass

    same_month = re.match(r"^([A-Za-z]+)\s+(\d+)-(\d+),\s*(\d{4})$", date_text)
    if same_month:
        month_str, start_day, end_day, year = same_month.groups()
        try:
            start = datetime.strptime(f"{month_str} {start_day}, {year}", "%b %d, %Y")
            end = datetime.strptime(f"{month_str} {end_day}, {year}", "%b %d, %Y")
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        except ValueError:
            pass

    cross_month = re.match(r"^([A-Za-z]+)\s+(\d+)-([A-Za-z]+)\s+(\d+),\s*(\d{4})$", date_text)
    if cross_month:
        start_month, start_day, end_month, end_day, year = cross_month.groups()
        try:
            start = datetime.strptime(f"{start_month} {start_day}, {year}", "%b %d, %Y")
            end = datetime.strptime(f"{end_month} {end_day}, {year}", "%b %d, %Y")
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None, None


def init_fox_session(max_retries=3):
    if cloudscraper:
        session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False, "desktop": True}
        )
    else:
        session = requests.Session()

    session.headers.update(FOX_THEATRE_AJAX_HEADERS)

    for attempt in range(max_retries):
        try:
            resp = session.get(f"{FOX_THEATRE_BASE}/events", timeout=20)
            if resp.status_code == 200:
                time.sleep(random.uniform(0.5, 1.5))
                return session
        except Exception:
            pass

        if attempt < max_retries - 1:
            time.sleep(random.uniform(2, 4))

    return session


def scrape_fox_ajax_all_events():
    events = []
    seen_urls = set()
    offset = 0
    per_page = 60
    max_retries = 5

    session = init_fox_session()

    while True:
        ajax_url = f"{FOX_THEATRE_BASE}/events/events_ajax/{offset}?category=0&venue=0&team=0&exclude=&per_page={per_page}&came_from_page=event-list-page"

        resp = None
        last_error = None
        for attempt in range(max_retries):
            try:
                resp = session.get(ajax_url, timeout=20)

                if resp.status_code == 406:
                    if attempt < max_retries - 1:
                        wait = (3 ** attempt) * 2 + random.uniform(2, 5)
                        print(f"    Fox Theatre: 406 error, refreshing session (attempt {attempt + 1}/{max_retries})...")
                        time.sleep(wait)
                        session = init_fox_session()
                        continue
                    else:
                        raise requests.exceptions.HTTPError(f"406 Client Error after {max_retries} retries")

                resp.raise_for_status()
                break

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = (3 ** attempt) * 2 + random.uniform(2, 5)
                    time.sleep(wait)
                    session = init_fox_session()
                else:
                    raise

        if resp is None:
            raise last_error or Exception("Failed to fetch Fox Theatre events")

        try:
            html = json.loads(resp.text)
        except json.JSONDecodeError:
            html = resp.text

        if not html.strip() or '<div class="eventItem' not in html:
            break

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.eventItem")

        if not cards:
            break

        for card in cards:
            title_el = card.select_one("h3.title a, h3.title, .title a")
            if title_el:
                title = title_el.get_text(strip=True)
            else:
                link = card.select_one("a[title*='More Info']")
                title = link.get("title", "").replace("More Info for ", "") if link else None

            if not title:
                continue

            detail_link = card.select_one("h3.title a, a.more, a[href*='/events/detail/']")
            if not detail_link:
                continue
            detail_url = detail_link.get("href", "")
            if not detail_url.startswith("http"):
                detail_url = FOX_THEATRE_BASE + detail_url

            if detail_url in seen_urls:
                continue
            seen_urls.add(detail_url)

            date_div = card.select_one("div.date")
            if date_div:
                month = date_div.select_one(".m-date__month")
                day = date_div.select_one(".m-date__day")
                year = date_div.select_one(".m-date__year")

                if month and day and year:
                    range_end = date_div.select_one(".m-date__rangeLast")
                    if range_end:
                        end_month = range_end.select_one(".m-date__month")
                        end_day = range_end.select_one(".m-date__day")
                        date_text = f"{month.get_text(strip=True)} {day.get_text(strip=True)}-{end_month.get_text(strip=True) + ' ' if end_month else ''}{end_day.get_text(strip=True)}{year.get_text(strip=True)}"
                    else:
                        date_text = f"{month.get_text(strip=True)} {day.get_text(strip=True)}{year.get_text(strip=True)}"
                else:
                    date_text = date_div.get_text(strip=True)
            else:
                card_text = card.get_text()
                date_match = re.search(r"([A-Z][a-z]{2,}\s+\d+(?:-(?:[A-Z][a-z]{2,}\s+)?\d+)?,\s*\d{4})", card_text)
                date_text = date_match.group(1) if date_match else None

            if not date_text:
                continue

            start_date, end_date = parse_fox_date_range(date_text)
            if not start_date:
                continue

            img = card.select_one("div.thumb img, .thumb img, img")
            image_url = None
            if img:
                image_url = img.get("src") or img.get("data-src")
                if image_url and not image_url.startswith("http"):
                    image_url = FOX_THEATRE_BASE + image_url

            ticket_link = card.select_one("a.tickets, a[href*='evenue.net']")
            ticket_url = ticket_link.get("href").strip() if ticket_link else detail_url

            card_classes = card.get("class", [])
            if "broadway" in card_classes:
                fox_category = "broadway"
            elif "comedy" in card_classes:
                fox_category = "comedy"
            elif "concerts" in card_classes:
                fox_category = "concerts"
            else:
                fox_category = "misc"

            events.append({
                "title": title,
                "date": start_date,
                "end_date": end_date if end_date != start_date else None,
                "info_url": detail_url,
                "ticket_url": ticket_url,
                "image_url": image_url,
                "fox_category": fox_category,
            })

        if len(cards) < per_page:
            break

        offset += len(cards)
        time.sleep(random.uniform(2.0, 4.0))

    return events


def scrape_fox_theatre():
    """Scrape events from Fox Theatre using the AJAX API endpoint."""
    try:
        ajax_events = scrape_fox_ajax_all_events()
        print(f"    Fox Theatre AJAX API: {len(ajax_events)} events")

        events = []
        for event in ajax_events:
            events.append({
                "venue": "Fox Theatre",
                "date": event["date"],
                "doors_time": None,
                "show_time": None,
                "artists": [{"name": event["title"]}],
                "ticket_url": event["ticket_url"],
                "info_url": event["info_url"],
                "image_url": event["image_url"],
                "category": event["fox_category"],
            })

        return events
    except Exception as e:
        try:
            with open(config.OUTPUT_PATH, "r") as f:
                cached = json.load(f)
            fallback_events = [evt for evt in cached if evt.get("venue") == "Fox Theatre"]
            if fallback_events:
                print(f"    Fox Theatre: using cached events ({len(fallback_events)}) due to error: {e}")
                return fallback_events
        except Exception:
            pass
        raise
