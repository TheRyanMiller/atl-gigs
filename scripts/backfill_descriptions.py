#!/usr/bin/env python3
"""One-off backfill for missing event descriptions in events.json."""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scraper import config  # noqa: E402
from scraper.utils.descriptions import clean_description, extract_first_description  # noqa: E402


DEFAULT_EVENTS_PATH = REPO_ROOT / "atl-gigs" / "public" / "events" / "events.json"
DEFAULT_R2_EVENTS_URL = f"{config.R2_PUBLIC_URL}/events.json"
AEG_SOURCES = {
    "Terminal West": "https://aegwebprod.blob.core.windows.net/json/events/211/events.json",
    "The Eastern": "https://aegwebprod.blob.core.windows.net/json/events/127/events.json",
    "Variety Playhouse": "https://aegwebprod.blob.core.windows.net/json/events/214/events.json",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = (8, 20)


def main():
    args = parse_args()
    started_at = datetime.now().isoformat(timespec="seconds")
    log(f"Starting description backfill at {started_at}")
    log(f"Input: {args.input}")
    log(f"Output: {args.output}")
    log(f"Today cutoff: {args.today}")
    log(f"Delay between requests: {args.delay}s")
    if args.limit:
        log(f"Attempt limit: {args.limit}")
    if args.dry_run:
        log("Dry run: output file will not be written")

    events = load_events(args.input)
    log(f"Loaded {len(events)} events")

    session = requests.Session()
    session.headers.update(HEADERS)
    html_cache = {}
    tm_cache = {}
    aeg_cache = {}

    candidates = [
        event for event in events
        if not event.get("description") and event.get("date", "") >= args.today
    ]
    log(f"Future events missing descriptions: {len(candidates)}")

    stats = {
        "attempted": 0,
        "updated": 0,
        "unsupported": 0,
        "empty": 0,
        "errors": 0,
        "skipped_limit": 0,
    }

    for index, event in enumerate(candidates, start=1):
        label = event_label(event)
        if args.limit and stats["attempted"] >= args.limit:
            stats["skipped_limit"] = len(candidates) - index + 1
            log(f"[{index}/{len(candidates)}] STOP limit reached; {stats['skipped_limit']} candidates not processed")
            break

        try:
            description, source = fetch_description_for_event(
                event,
                session=session,
                html_cache=html_cache,
                tm_cache=tm_cache,
                aeg_cache=aeg_cache,
                delay=args.delay,
            )
            if source is None:
                stats["unsupported"] += 1
                log(f"[{index}/{len(candidates)}] SKIP unsupported source | {label}")
                continue

            stats["attempted"] += 1
            if description:
                event["description"] = description
                stats["updated"] += 1
                log(
                    f"[{index}/{len(candidates)}] UPDATED {source} "
                    f"({len(description)} chars) | {label}"
                )
            else:
                stats["empty"] += 1
                log(f"[{index}/{len(candidates)}] EMPTY {source} | {label}")
        except Exception as e:
            stats["attempted"] += 1
            stats["errors"] += 1
            log(f"[{index}/{len(candidates)}] ERROR {safe_error(e)} | {label}")

    log(
        "Summary: "
        f"{stats['updated']} updated, "
        f"{stats['empty']} empty, "
        f"{stats['unsupported']} unsupported, "
        f"{stats['errors']} errors, "
        f"{stats['skipped_limit']} skipped by limit, "
        f"{stats['attempted']} attempted"
    )

    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(events, f, indent=2)
        log(f"Wrote {len(events)} events to {args.output}")
        if args.upload_r2:
            upload_events_to_r2(args.output)


def parse_args():
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_EVENTS_PATH,
        help="Path to events.json to read.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_EVENTS_PATH,
        help="Path to events.json to write.",
    )
    parser.add_argument(
        "--today",
        default=today,
        help="YYYY-MM-DD cutoff; only events on/after this date are backfilled.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Delay after each network request.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum supported events to attempt; 0 means no limit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and log progress without writing output.",
    )
    parser.add_argument(
        "--fetch-r2",
        action="store_true",
        help="Download the current public R2 events.json before backfilling.",
    )
    parser.add_argument(
        "--upload-r2",
        action="store_true",
        help="Upload the rewritten events.json to Cloudflare R2 after a successful write.",
    )
    args = parser.parse_args()

    args.input = args.input.resolve()
    args.output = args.output.resolve()
    if args.fetch_r2:
        fetch_r2_events(args.input)

    return args


def fetch_r2_events(output_path):
    log(f"Fetching current R2 events from {DEFAULT_R2_EVENTS_URL}")
    resp = requests.get(DEFAULT_R2_EVENTS_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(resp.text)
    log(f"Saved R2 events to {output_path}")


def upload_events_to_r2(path):
    try:
        import boto3  # type: ignore
    except ImportError:
        log("R2 upload skipped: boto3 is not installed")
        return False

    if not all([config.R2_ACCOUNT_ID, config.R2_ACCESS_KEY_ID, config.R2_SECRET_ACCESS_KEY]):
        log("R2 upload skipped: missing R2 credentials")
        return False

    log("Uploading updated events.json to R2")
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=config.R2_ACCESS_KEY_ID,
        aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
    )
    with open(path, "rb") as f:
        s3.put_object(
            Bucket=config.R2_BUCKET_NAME,
            Key="events.json",
            Body=f.read(),
            ContentType="application/json",
        )
    log("Uploaded updated events.json to R2")
    return True


def load_events(path):
    with open(path, "r") as f:
        events = json.load(f)
    if not isinstance(events, list):
        raise ValueError(f"{path} does not contain a JSON array")
    return events


def fetch_description_for_event(event, session, html_cache, tm_cache, aeg_cache, delay):
    heading = event_heading(event)
    info_url = event.get("info_url")
    venue = event.get("venue")

    if venue in AEG_SOURCES:
        return fetch_aeg_description(event, aeg_cache, session, delay), "aeg"

    if info_url:
        source = source_for_info_url(info_url)
        if source == "masquerade":
            return (
                fetch_masquerade_description(info_url, heading, session, html_cache, delay),
                source,
            )
        if source:
            selectors = {
                "earl": [".band-details .band-info"],
                "center_stage": [".event-artist .description", ".description-section .description"],
                "fox": ['meta[name="description"]', 'meta[property="og:description"]'],
                "mercedes_benz_stadium": [".event-details-desc.w-richtext", ".event-details-desc"],
                "state_farm_arena": [".event_description"],
            }[source]
            return (
                fetch_html_description(info_url, selectors, heading, session, html_cache, delay),
                source,
            )

    if venue in {"Tabernacle", "Coca-Cola Roxy"}:
        return None, None

    tm_event_id = extract_ticketmaster_event_id(event.get("ticket_url"))
    if tm_event_id and config.TM_API_KEY:
        return fetch_tm_description(tm_event_id, heading, session, tm_cache, delay), "ticketmaster"

    return None, None


def source_for_info_url(url):
    if "badearl.com/show/" in url:
        return "earl"
    if "centerstage-atlanta.com/events/" in url:
        return "center_stage"
    if "foxtheatre.org/events/detail/" in url:
        return "fox"
    if "masqueradeatlanta.com/events/" in url:
        return "masquerade"
    if "mercedesbenzstadium.com/events/" in url:
        return "mercedes_benz_stadium"
    if "statefarmarena.com/events/detail/" in url:
        return "state_farm_arena"
    return None


def fetch_html_description(url, selectors, heading, session, html_cache, delay):
    html = fetch_html(url, session, html_cache, delay)
    soup = BeautifulSoup(html, "html.parser")
    return extract_first_description(soup, selectors, heading=heading)


def fetch_masquerade_description(url, heading, session, html_cache, delay):
    html = fetch_html(url, session, html_cache, delay)
    soup = BeautifulSoup(html, "html.parser")

    for bio in soup.select(".attractions .attraction-bio"):
        title_el = bio.select_one(".attraction_title")
        title = title_el.get_text(" ", strip=True) if title_el else heading
        if not same_artist_name(title, heading):
            continue

        description = clean_description(str(bio), heading=title)
        if description:
            return description

    return None


def fetch_tm_description(event_id, heading, session, tm_cache, delay):
    if event_id not in tm_cache:
        resp = session.get(
            f"{config.TM_BASE_URL}/events/{event_id}.json",
            params={"apikey": config.TM_API_KEY},
            timeout=TIMEOUT,
        )
        if resp.status_code == 404:
            tm_cache[event_id] = {}
            return None
        resp.raise_for_status()
        tm_cache[event_id] = resp.json()
        sleep(delay)

    data = tm_cache[event_id] or {}
    return clean_description(data.get("info"), heading=heading or data.get("name"))


def fetch_aeg_description(event, aeg_cache, session, delay):
    venue = event.get("venue")
    ticket_url = event.get("ticket_url")
    if venue not in AEG_SOURCES or not ticket_url:
        return None

    if venue not in aeg_cache:
        resp = session.get(AEG_SOURCES[venue], timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        aeg_cache[venue] = {
            item.get("ticketing", {}).get("url"): item
            for item in data.get("events", [])
            if item.get("ticketing", {}).get("url")
        }
        sleep(delay)

    source_event = aeg_cache[venue].get(ticket_url)
    if not source_event:
        return None

    return clean_description(
        source_event.get("bio") or source_event.get("description"),
        heading=event_heading(event),
    )


def fetch_html(url, session, html_cache, delay):
    if url not in html_cache:
        resp = session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        html_cache[url] = resp.text
        sleep(delay)
    return html_cache[url]


def extract_ticketmaster_event_id(url):
    if not url:
        return None
    match = re.search(r"/event/([A-Za-z0-9]+)", url)
    return match.group(1) if match else None


def event_heading(event):
    artists = event.get("artists") or []
    if artists and artists[0].get("name"):
        return artists[0]["name"]
    return None


def event_label(event):
    artist = event_heading(event) or "Unknown"
    return f"{event.get('date')} | {event.get('venue')} | {artist} | {event.get('slug')}"


def normalize_artist_name(value):
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def same_artist_name(a, b):
    normalized_a = normalize_artist_name(a)
    normalized_b = normalize_artist_name(b)
    return bool(
        normalized_a
        and normalized_b
        and (
            normalized_a == normalized_b
            or normalized_a in normalized_b
            or normalized_b in normalized_a
        )
    )


def sleep(delay):
    if delay > 0:
        time.sleep(delay)


def safe_error(error):
    message = str(error)
    if config.TM_API_KEY:
        message = message.replace(config.TM_API_KEY, "[redacted]")
    message = re.sub(r"apikey=[^&\\s]+", "apikey=[redacted]", message)
    return f"{type(error).__name__}: {message}"


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


if __name__ == "__main__":
    main()
