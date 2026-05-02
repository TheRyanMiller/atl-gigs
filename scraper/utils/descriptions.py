import html
import re

from bs4 import BeautifulSoup


SOCIAL_LINK_TEXT = {
    "bandcamp",
    "facebook",
    "fb event",
    "instagram",
    "read more",
    "share",
    "spotify",
    "tiktok",
    "twitter",
    "website",
    "youtube",
}

LOGISTICS_KEYWORDS = [
    "ada",
    "all ages",
    "bag",
    "balconies",
    "box office",
    "doors",
    "elevator",
    "entry",
    "event organizer",
    "floor is general admission",
    "general admission",
    "mobile tickets",
    "parking",
    "phone-free",
    "pouches",
    "purchase",
    "reserved assigned seating",
    "seating",
    "show at",
    "terms",
    "ticketmaster",
    "ticket transfer",
    "tickets",
    "transfer will be delayed",
]

PROMO_KEYWORDS = [
    "album",
    "artist",
    "band",
    "debut",
    "formed",
    "genre",
    "music",
    "performed",
    "record",
    "released",
    "singer",
    "song",
    "songwriter",
    "tour",
]


def clean_description(value, heading=None):
    """Return cleaned plain text for event descriptions, or None if unusable."""
    if not value or not isinstance(value, str):
        return None

    text = _plain_text(value)
    if heading:
        text = _remove_leading_heading(text, heading)

    text = _drop_social_lines(text)
    text = _normalize_description_text(text)

    if not text or _looks_logistics_only(text):
        return None

    return text


def extract_first_description(soup, selectors, heading=None):
    """Extract the first usable description from a BeautifulSoup document."""
    for selector in selectors:
        for element in soup.select(selector):
            value = element.get("content") if element.name == "meta" else str(element)
            description = clean_description(value, heading=heading)
            if description:
                return description
    return None


def _plain_text(value):
    soup = BeautifulSoup(value, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")

    text = soup.get_text("\n", strip=True)
    text = html.unescape(text).replace("\xa0", " ")
    return text


def _normalize_description_text(text):
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n\n".join(lines).strip()


def _drop_social_lines(text):
    lines = []
    for line in text.splitlines():
        normalized = re.sub(r"\s+", " ", line).strip()
        if not normalized:
            continue
        if normalized.lower() in SOCIAL_LINK_TEXT:
            continue
        lines.append(normalized)
    return "\n".join(lines)


def _remove_leading_heading(text, heading):
    normalized_heading = re.sub(r"\s+", " ", heading or "").strip()
    if not normalized_heading:
        return text

    heading_pattern = r"\s+".join(re.escape(part) for part in normalized_heading.split())
    return re.sub(
        rf"^\s*{heading_pattern}\s*[-:\n\t]*",
        "",
        text or "",
        count=1,
        flags=re.IGNORECASE,
    ).strip()


def _looks_logistics_only(text):
    lower = text.lower()
    word_count = len(re.findall(r"\w+", lower))
    logistics_hits = sum(1 for keyword in LOGISTICS_KEYWORDS if keyword in lower)
    promo_hits = sum(1 for keyword in PROMO_KEYWORDS if keyword in lower)

    if word_count < 5:
        return True
    if logistics_hits >= 4 and promo_hits == 0:
        return True
    if logistics_hits >= 6 and promo_hits <= 1:
        return True

    return False
