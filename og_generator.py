#!/usr/bin/env python3
"""
Generate Open Graph images for ATL Gigs events.
Creates social media preview images with:
- Artist photo as background
- Date badge in top-left corner (matching the site design)
- ATL Gigs branding in bottom-right
- Dark gradient overlay for readability
"""

import requests
import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# Image dimensions for OG (1200x630 is the standard)
OG_WIDTH = 1200
OG_HEIGHT = 630

# Paths
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "atl-gigs" / "public" / "og"
FONTS_DIR = SCRIPT_DIR / "fonts"

# Colors (matching the site theme)
TEAL_600 = (13, 148, 136)  # teal-600 (gradient start)
CYAN_600 = (8, 145, 178)   # cyan-600 (gradient end)
TEAL_500 = (20, 184, 166)  # teal-500 (for text)
DARK_BG = (10, 10, 10)     # neutral-950
BADGE_BG = (10, 10, 10, 200)  # Semi-transparent dark
WHITE = (255, 255, 255)
LIGHT_GRAY = (163, 163, 163)  # neutral-400


def download_image(url: str, timeout: int = 10) -> Image.Image | None:
    """Download an image from URL and return as PIL Image."""
    if not url:
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        print(f"  Warning: Could not download image from {url}: {e}")
        return None


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font at the specified size. Falls back to default if custom fonts unavailable."""
    try:
        # Try Montserrat first (matches the site)
        font_name = "Montserrat-Bold.ttf" if bold else "Montserrat-Regular.ttf"
        font_path = FONTS_DIR / font_name
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size)

        # Try system fonts
        system_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
        for font in system_fonts:
            if Path(font).exists():
                return ImageFont.truetype(font, size)
    except Exception:
        pass

    # Fall back to default
    return ImageFont.load_default()


def create_gradient_overlay(width: int, height: int) -> Image.Image:
    """Create a dark gradient overlay for better text readability."""
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Bottom gradient (stronger for branding area)
    for y in range(height // 2, height):
        alpha = int(180 * ((y - height // 2) / (height // 2)))
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    # Top-left corner gradient for date badge area
    for y in range(height // 3):
        alpha = int(100 * (1 - y / (height // 3)))
        draw.line([(0, y), (width // 3, y)], fill=(0, 0, 0, alpha))

    return overlay


def draw_rounded_rect(draw: ImageDraw.Draw, xy: tuple, radius: int, fill: tuple):
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
    draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
    draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
    draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)


def create_gradient_rounded_rect(width: int, height: int, radius: int,
                                  color1: tuple, color2: tuple) -> Image.Image:
    """Create a rounded rectangle with diagonal gradient fill."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Create gradient
    for y in range(height):
        for x in range(width):
            # Diagonal gradient factor (0 to 1)
            factor = (x + y) / (width + height)
            r = int(color1[0] + (color2[0] - color1[0]) * factor)
            g = int(color1[1] + (color2[1] - color1[1]) * factor)
            b = int(color1[2] + (color2[2] - color1[2]) * factor)
            img.putpixel((x, y), (r, g, b, 255))

    # Create rounded mask
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)

    img.putalpha(mask)
    return img


def generate_og_image(event: dict) -> str | None:
    """
    Generate an OG image for an event.
    Returns the relative path to the generated image, or None if failed.
    Skips generation if image already exists.
    """
    slug = event.get("slug")
    if not slug:
        return None

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{slug}.png"

    # Skip if already exists (cron runs daily, no need to regenerate)
    if output_path.exists():
        return f"/og/{slug}.png"

    # Create base image
    img = Image.new("RGBA", (OG_WIDTH, OG_HEIGHT), DARK_BG)

    # Try to get artist image as background
    artist_img = download_image(event.get("image_url"))
    if artist_img:
        # Resize and crop to fill
        img_ratio = artist_img.width / artist_img.height
        target_ratio = OG_WIDTH / OG_HEIGHT

        if img_ratio > target_ratio:
            # Image is wider, scale by height
            new_height = OG_HEIGHT
            new_width = int(new_height * img_ratio)
        else:
            # Image is taller, scale by width
            new_width = OG_WIDTH
            new_height = int(new_width / img_ratio)

        artist_img = artist_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Center crop
        left = (new_width - OG_WIDTH) // 2
        top = (new_height - OG_HEIGHT) // 2
        artist_img = artist_img.crop((left, top, left + OG_WIDTH, top + OG_HEIGHT))

        # Slightly darken the background image
        darkened = Image.new("RGBA", (OG_WIDTH, OG_HEIGHT), (0, 0, 0, 80))
        artist_img = Image.alpha_composite(artist_img, darkened)

        img.paste(artist_img, (0, 0))

    # Add gradient overlay
    gradient = create_gradient_overlay(OG_WIDTH, OG_HEIGHT)
    img = Image.alpha_composite(img, gradient)

    draw = ImageDraw.Draw(img)

    # Parse date for badge
    try:
        event_date = datetime.strptime(event.get("date", ""), "%Y-%m-%d")
        month = event_date.strftime("%b").upper()
        day = str(event_date.day)
    except:
        month = "TBD"
        day = "?"

    # Draw date badge (top-left, matching site design) - 50% larger than original
    badge_x, badge_y = 40, 40
    badge_w, badge_h = 150, 150  # Increased from 100x100

    # Badge background with rounded corners (dark semi-transparent)
    badge_overlay = Image.new("RGBA", (OG_WIDTH, OG_HEIGHT), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge_overlay)
    draw_rounded_rect(badge_draw,
                      (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
                      20, (10, 10, 10, 200))
    img = Image.alpha_composite(img, badge_overlay)
    draw = ImageDraw.Draw(img)

    # Month text (small, teal) - scaled up
    month_font = get_font(28, bold=True)
    month_bbox = draw.textbbox((0, 0), month, font=month_font)
    month_width = month_bbox[2] - month_bbox[0]
    draw.text((badge_x + (badge_w - month_width) // 2, badge_y + 28),
              month, font=month_font, fill=TEAL_500)

    # Day text (large, white) - scaled up
    day_font = get_font(72, bold=True)
    day_bbox = draw.textbbox((0, 0), day, font=day_font)
    day_width = day_bbox[2] - day_bbox[0]
    draw.text((badge_x + (badge_w - day_width) // 2, badge_y + 58),
              day, font=day_font, fill=WHITE)

    # Draw ATL Gigs logo in bottom-right (matching site header style)
    # Create gradient icon square
    icon_size = 80
    icon_radius = 20
    icon_img = create_gradient_rounded_rect(icon_size, icon_size, icon_radius, TEAL_600, CYAN_600)

    # Draw music note icon (two notes connected by beam - like the site)
    icon_draw = ImageDraw.Draw(icon_img)
    # Draw two vertical stems
    stem_color = WHITE
    # Left note
    icon_draw.rectangle([22, 18, 26, 52], fill=stem_color)
    # Right note
    icon_draw.rectangle([50, 24, 54, 58], fill=stem_color)
    # Connecting beam at top
    icon_draw.polygon([(22, 18), (54, 24), (54, 30), (22, 24)], fill=stem_color)
    # Left note head (oval)
    icon_draw.ellipse([14, 48, 30, 62], fill=stem_color)
    # Right note head (oval)
    icon_draw.ellipse([42, 54, 58, 68], fill=stem_color)

    # Calculate text dimensions first to size the background properly
    atl_font = get_font(48, bold=True)
    gigs_font = get_font(48, bold=True)
    url_font = get_font(20, bold=False)

    atl_bbox = draw.textbbox((0, 0), "ATL", font=atl_font)
    gigs_bbox = draw.textbbox((0, 0), "Gigs", font=gigs_font)
    atl_width = atl_bbox[2] - atl_bbox[0]
    gigs_width = gigs_bbox[2] - gigs_bbox[0]
    text_total_width = atl_width + gigs_width + 8

    # Create dark rounded background - sized to fit content with padding
    logo_padding = 20
    logo_bg_w = icon_size + text_total_width + logo_padding * 3 + 15
    logo_bg_h = icon_size + logo_padding * 2
    logo_bg_x = OG_WIDTH - logo_bg_w - 30
    logo_bg_y = OG_HEIGHT - logo_bg_h - 30

    logo_bg_overlay = Image.new("RGBA", (OG_WIDTH, OG_HEIGHT), (0, 0, 0, 0))
    logo_bg_draw = ImageDraw.Draw(logo_bg_overlay)
    draw_rounded_rect(logo_bg_draw,
                      (logo_bg_x, logo_bg_y, logo_bg_x + logo_bg_w, logo_bg_y + logo_bg_h),
                      20, (10, 10, 10, 210))
    img = Image.alpha_composite(img, logo_bg_overlay)

    # Position icon with padding from edge
    icon_x = logo_bg_x + logo_padding
    icon_y = logo_bg_y + (logo_bg_h - icon_size) // 2
    img.paste(icon_img, (icon_x, icon_y), icon_img)

    draw = ImageDraw.Draw(img)

    # Draw "ATL" text in white
    text_x = icon_x + icon_size + 15
    text_y = logo_bg_y + logo_padding + 2
    draw.text((text_x, text_y), "ATL", font=atl_font, fill=WHITE)

    # Draw "Gigs" text in teal
    draw.text((text_x + atl_width + 4, text_y), "Gigs", font=gigs_font, fill=TEAL_500)

    # Add URL below
    draw.text((text_x, text_y + 52), "atl-gigs.info", font=url_font, fill=LIGHT_GRAY)

    # Draw event info (bottom-left area)
    info_y = OG_HEIGHT - 180

    # Artist name - only show the headliner (first artist)
    artists = event.get("artists", [{}])
    artist_name = artists[0].get("name", "TBA") if artists else "TBA"

    # If artist name contains multiple artists (comma, &, etc.), take only the first
    for sep in [",", " & ", " and ", " with ", " featuring ", " feat. ", " ft. "]:
        if sep in artist_name:
            artist_name = artist_name.split(sep)[0].strip()
            break

    # Truncate if still too long (leave room for logo on right)
    if len(artist_name) > 25:
        artist_name = artist_name[:22] + "..."

    artist_font = get_font(56, bold=True)
    draw.text((40, info_y), artist_name, font=artist_font, fill=WHITE)

    # Venue and formatted date
    venue = event.get("venue", "")
    try:
        date_str = event_date.strftime("%B %d, %Y")
    except:
        date_str = event.get("date", "")

    detail_text = f"{venue}  •  {date_str}"
    detail_font = get_font(28, bold=False)
    draw.text((40, info_y + 70), detail_text, font=detail_font, fill=LIGHT_GRAY)

    # Save the image
    try:
        img.convert("RGB").save(output_path, "PNG", optimize=True)
        return f"/og/{slug}.png"
    except Exception as e:
        print(f"  Error saving OG image for {slug}: {e}")
        return None


def generate_default_og_image():
    """Generate a default OG image for the homepage."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "default.png"

    img = Image.new("RGBA", (OG_WIDTH, OG_HEIGHT), DARK_BG)
    draw = ImageDraw.Draw(img)

    # Add subtle gradient overlay
    for y in range(OG_HEIGHT):
        alpha = int(30 * (y / OG_HEIGHT))
        draw.line([(0, y), (OG_WIDTH, y)], fill=(20, 184, 166, alpha))

    # Create large gradient icon square (centered)
    icon_size = 120
    icon_radius = 30
    icon_img = create_gradient_rounded_rect(icon_size, icon_size, icon_radius, TEAL_600, CYAN_600)

    # Add music note to icon
    icon_draw = ImageDraw.Draw(icon_img)
    note_font = get_font(60, bold=True)
    icon_draw.text((icon_size // 2 - 20, icon_size // 2 - 35), "♪", font=note_font, fill=WHITE)

    # Position icon centered, slightly above middle
    icon_x = (OG_WIDTH - icon_size) // 2
    icon_y = OG_HEIGHT // 2 - 120
    img.paste(icon_img, (icon_x, icon_y), icon_img)

    draw = ImageDraw.Draw(img)

    # Draw "ATL" in white and "Gigs" in teal (centered below icon)
    title_font = get_font(80, bold=True)
    atl_bbox = draw.textbbox((0, 0), "ATL", font=title_font)
    gigs_bbox = draw.textbbox((0, 0), "Gigs", font=title_font)
    atl_width = atl_bbox[2] - atl_bbox[0]
    gigs_width = gigs_bbox[2] - gigs_bbox[0]
    total_width = atl_width + gigs_width + 10

    title_x = (OG_WIDTH - total_width) // 2
    title_y = icon_y + icon_size + 30
    draw.text((title_x, title_y), "ATL", font=title_font, fill=WHITE)
    draw.text((title_x + atl_width + 10, title_y), "Gigs", font=title_font, fill=TEAL_500)

    # Tagline
    tagline = "Live music events in Atlanta"
    tagline_font = get_font(32, bold=False)
    tagline_bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
    tagline_width = tagline_bbox[2] - tagline_bbox[0]
    draw.text(((OG_WIDTH - tagline_width) // 2, OG_HEIGHT - 130),
              tagline, font=tagline_font, fill=WHITE)

    # URL
    url_font = get_font(24, bold=False)
    url_text = "atl-gigs.info"
    url_bbox = draw.textbbox((0, 0), url_text, font=url_font)
    url_width = url_bbox[2] - url_bbox[0]
    draw.text(((OG_WIDTH - url_width) // 2, OG_HEIGHT - 80),
              url_text, font=url_font, fill=TEAL_500)

    img.convert("RGB").save(output_path, "PNG", optimize=True)
    print(f"Generated default OG image: {output_path}")
    return "/og/default.png"


if __name__ == "__main__":
    # Test with a sample event
    test_event = {
        "slug": "test-event",
        "date": "2025-12-15",
        "venue": "The Tabernacle",
        "artists": [{"name": "Test Artist"}],
        "image_url": None
    }

    print("Generating default OG image...")
    generate_default_og_image()

    print("Generating test event OG image...")
    result = generate_og_image(test_event)
    print(f"Result: {result}")
