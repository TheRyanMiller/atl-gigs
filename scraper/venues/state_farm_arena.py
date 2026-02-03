import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from scraper.utils.categories import detect_category_from_text, detect_category_from_ticket_url
from scraper.utils.dates import normalize_time

STATE_FARM_ARENA_BASE = "https://www.statefarmarena.com"
STATE_FARM_ARENA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

STATE_FARM_ARENA_CATEGORIES = {
    "/events/category/concerts": "concerts",
    "/events/category/family-shows": "misc",
    "/events/category/hawks": "sports",
    "/events/category/other": "misc",
}


def scrape_state_farm_arena():
    """Scrape events from State Farm Arena using HTML parsing."""
    all_events = {}
    category_priority = {"concerts": 0, "comedy": 1, "broadway": 2, "sports": 3, "misc": 4}

    def parse_date(date_div):
        if not date_div:
            return None, None

        single = date_div.select_one(".m-date__singleDate")
        if single:
            month = single.select_one(".m-date__month")
            day = single.select_one(".m-date__day")
            year = single.select_one(".m-date__year")
            if month and day and year:
                try:
                    date_str = f"{month.get_text(strip=True)} {day.get_text(strip=True)}, {year.get_text(strip=True)}"
                    dt = datetime.strptime(date_str, "%b %d, %Y")
                    return dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass

        range_first = date_div.select_one(".m-date__rangeFirst")
        range_last = date_div.select_one(".m-date__rangeLast")
        if range_first:
            month = range_first.select_one(".m-date__month")
            day = range_first.select_one(".m-date__day")
            year = range_first.select_one(".m-date__year") or date_div.select_one(".m-date__year")
            if month and day and year:
                try:
                    date_str = f"{month.get_text(strip=True)} {day.get_text(strip=True)}, {year.get_text(strip=True)}"
                    start_dt = datetime.strptime(date_str, "%b %d, %Y")
                    start_date = start_dt.strftime("%Y-%m-%d")

                    end_date = start_date
                    if range_last:
                        end_month = range_last.select_one(".m-date__month") or month
                        end_day = range_last.select_one(".m-date__day")
                        end_year = range_last.select_one(".m-date__year") or year
                        if end_day:
                            try:
                                end_str = f"{end_month.get_text(strip=True)} {end_day.get_text(strip=True)}, {end_year.get_text(strip=True)}"
                                end_dt = datetime.strptime(end_str, "%b %d, %Y")
                                end_date = end_dt.strftime("%Y-%m-%d")
                            except ValueError:
                                pass
                    return start_date, end_date
                except ValueError:
                    pass

        return None, None

    def parse_time(meta_div):
        if not meta_div:
            return None
        time_el = meta_div.select_one(".time")
        if time_el:
            time_text = time_el.get_text(strip=True)
            match = re.search(r"(\d{1,2}:\d{2})\s*(AM|PM)", time_text, re.IGNORECASE)
            if match:
                return normalize_time(f"{match.group(1)}{match.group(2)}")
        return None

    def scrape_page(url, category):
        resp = requests.get(url, headers=STATE_FARM_ARENA_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        events = []

        for card in soup.select(".eventItem"):
            title_el = card.select_one(".title a, .title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            detail_link = card.select_one("a.more, a[href*='/events/detail/']")
            if detail_link:
                detail_url = detail_link.get("href", "")
                if not detail_url.startswith("http"):
                    detail_url = STATE_FARM_ARENA_BASE + detail_url
            else:
                detail_url = None

            ticket_link = card.select_one("a.tickets, a[href*='ticketmaster']")
            ticket_url = ticket_link.get("href", "") if ticket_link else detail_url

            if not ticket_url:
                continue

            date_div = card.select_one(".date")
            start_date, end_date = parse_date(date_div)
            if not start_date:
                continue

            meta_div = card.select_one(".meta")
            show_time = parse_time(meta_div)

            img = card.select_one(".thumb img, img")
            image_url = None
            if img:
                image_url = img.get("src") or img.get("data-src")
                if image_url and not image_url.startswith("http"):
                    image_url = STATE_FARM_ARENA_BASE + image_url

            final_category = category
            if category == "misc":
                detected = detect_category_from_text(title) or detect_category_from_ticket_url(ticket_url)
                if detected:
                    final_category = detected

            events.append({
                "name": title,
                "date": start_date,
                "end_date": end_date if end_date != start_date else None,
                "show_time": show_time,
                "detail_url": detail_url,
                "ticket_url": ticket_url,
                "image_url": image_url,
                "category": final_category,
            })

        load_more = soup.select_one("a.loadMore, a[href*='/events/index/']")
        next_url = None
        if load_more:
            next_href = load_more.get("href", "")
            if next_href and not next_href.startswith("http"):
                next_url = STATE_FARM_ARENA_BASE + next_href

        return events, next_url

    for path, category in STATE_FARM_ARENA_CATEGORIES.items():
        try:
            url = STATE_FARM_ARENA_BASE + path
            page_count = 0
            pages_scraped = 0
            max_pages = 10

            while url and pages_scraped < max_pages:
                page_events, next_url = scrape_page(url, category)
                pages_scraped += 1

                for event in page_events:
                    key = event["detail_url"] or event["ticket_url"]

                    if key in all_events:
                        existing = all_events[key]
                        existing_priority = category_priority.get(existing["category"], 99)
                        new_priority = category_priority.get(category, 99)
                        if new_priority < existing_priority:
                            all_events[key]["category"] = category
                    else:
                        all_events[key] = event
                        page_count += 1

                url = next_url
                if url:
                    time.sleep(0.3)

            print(f"    State Farm Arena {path}: {page_count} events ({pages_scraped} pages)")
        except Exception as e:
            print(f"    State Farm Arena {path}: ERROR - {e}")

    events = []
    for event in all_events.values():
        events.append({
            "venue": "State Farm Arena",
            "date": event["date"],
            "doors_time": None,
            "show_time": event["show_time"],
            "artists": [{"name": event["name"]}],
            "ticket_url": event["ticket_url"],
            "info_url": event["detail_url"],
            "image_url": event["image_url"],
            "category": event["category"],
        })

    print(f"    State Farm Arena total: {len(events)} events")
    return events
