import datetime as dt
import itertools
import random
import time

import requests
from bs4 import BeautifulSoup

from scraper import config
from scraper.utils.dates import normalize_time

EARL_BASE = "https://badearl.com/show-calendar/"
EARL_PAGE_Q = "?sf_paged={}"
EARL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def scrape_earl():
    """Scrape events from The Earl's website."""
    max_retries = 3

    def fetch_with_retry(url):
        for attempt in range(max_retries):
            try:
                r = requests.get(url, headers=EARL_HEADERS, timeout=30)
                if r.status_code == 200:
                    return r.text
                elif r.status_code >= 500:
                    if attempt < max_retries - 1:
                        wait = (2 ** attempt) * 2 + random.uniform(1, 3)
                        time.sleep(wait)
                        continue
                return None
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries - 1:
                    wait = (2 ** attempt) * 2 + random.uniform(1, 3)
                    print(f"    The Earl: Retry {attempt + 1}/{max_retries} after {type(e).__name__}...")
                    time.sleep(wait)
                else:
                    raise
        return None

    def pages():
        n = 1
        while True:
            url = EARL_BASE if n == 1 else EARL_BASE + EARL_PAGE_Q.format(n)
            text = fetch_with_retry(url)
            if text is None or "No results found." in text:
                break
            yield text
            n += 1
            time.sleep(random.uniform(1.0, 2.0))

    def parse_page(html):
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.cl-layout__item"):
            img = card.select_one("div.cl-element-featured_media img")
            image_url = img["src"] if img else None

            date_tag = card.select_one("p.show-listing-date")
            if not date_tag:
                continue
            date = dt.datetime.strptime(date_tag.text.strip(), "%A, %b. %d, %Y").date()

            times = [t.text.strip() for t in card.select("p.show-listing-time")]
            doors = times[0].split()[0] if times else None
            show = times[1].split()[0] if len(times) > 1 else None

            prices = [p.text.strip() for p in card.select("p.show-listing-price")]
            adv = next((p for p in prices if "ADV" in p), None)
            dos = next((p for p in prices if "DOS" in p), None)

            headliners = [h.text.strip() for h in card.select("div.show-listing-headliner")]
            supports = [s.text.strip() for s in card.select("div.show-listing-support")]
            artists = headliners + supports

            tix = card.find("a", string="TIX", href=True)
            info = card.find("a", string="More Info", href=True)

            yield {
                "venue": "The Earl",
                "date": str(date),
                "doors_time": normalize_time(doors),
                "show_time": normalize_time(show),
                "artists": [{"name": a} for a in artists],
                "adv_price": adv,
                "dos_price": dos,
                "ticket_url": tix["href"] if tix else None,
                "info_url": info["href"] if info else None,
                "image_url": image_url,
                "category": config.DEFAULT_CATEGORY,
            }

    return list(itertools.chain.from_iterable(parse_page(p) for p in pages()))
