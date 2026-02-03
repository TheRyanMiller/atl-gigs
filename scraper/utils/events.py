import re


def generate_slug(event):
    """
    Generate a unique slug for an event based on date, venue, stage, and artist.
    Format: YYYY-MM-DD-venue-name-stage-artist-name
    Stage is included for multi-room venues (e.g., The Masquerade).
    """
    date = event.get("date", "")
    venue = event.get("venue", "")
    stage = event.get("stage", "")
    artist = event.get("artists", [{}])[0].get("name", "unknown")

    def slugify(text):
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip("-")

    slug_parts = [date, slugify(venue), slugify(stage), slugify(artist)]
    return "-".join(filter(None, slug_parts))


def is_zero_price(price_str):
    """Check if a price string represents $0 or free."""
    if not price_str:
        return True
    zero_patterns = [r"^\$0(\.0+)?$", r"^\$0(\.0+)?\s*-\s*\$0(\.0+)?$"]
    price_clean = price_str.strip()
    for pattern in zero_patterns:
        if re.match(pattern, price_clean):
            return True
    return False


def normalize_price(event):
    """
    Consolidate price fields into a single 'price' field.
    Combines adv_price/dos_price from The Earl into standard format.
    Filters out $0 prices (often means price not available in API).
    """
    if "price" in event and event["price"]:
        price = event["price"]
    elif "adv_price" in event or "dos_price" in event:
        adv = event.get("adv_price", "")
        dos = event.get("dos_price", "")
        if adv and dos:
            adv_match = re.search(r"\$[\d.]+", adv)
            dos_match = re.search(r"\$[\d.]+", dos)
            if adv_match and dos_match:
                price = f"{adv_match.group()} ADV / {dos_match.group()} DOS"
            else:
                price = f"{adv} / {dos}"
        else:
            price = adv or dos
    else:
        price = None

    if is_zero_price(price):
        price = "See website"

    event.pop("adv_price", None)
    event.pop("dos_price", None)
    event["price"] = price
    return event
