import type { VercelRequest, VercelResponse } from "@vercel/node";

const SITE_URL = "https://atl-gigs.info";
const DEFAULT_OG_IMAGE = `${SITE_URL}/atlgigs.png`;

// User agent patterns for social media crawlers
const CRAWLER_PATTERNS = [
  "facebookexternalhit",
  "Facebot",
  "Twitterbot",
  "LinkedInBot",
  "Slackbot",
  "TelegramBot",
  "WhatsApp",
  "Discordbot",
  "Applebot",
  "Pinterest",
  "Embedly",
  "Quora",
  "vkShare",
  "Slack-ImgProxy",
];

function isCrawler(userAgent: string | null): boolean {
  if (!userAgent) return false;
  const ua = userAgent.toLowerCase();
  return CRAWLER_PATTERNS.some((pattern) => ua.includes(pattern.toLowerCase()));
}

function formatDateLong(dateStr: string): string {
  try {
    const date = new Date(dateStr + "T12:00:00");
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function formatDateShort(dateStr: string): string {
  try {
    const date = new Date(dateStr + "T12:00:00");
    return date.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Extract headliner from artist name
function getHeadliner(artistName: string): string {
  const separators = [",", " & ", " and ", " with ", " featuring ", " feat. ", " ft. "];
  for (const sep of separators) {
    if (artistName.includes(sep)) {
      return artistName.split(sep)[0].trim();
    }
  }
  return artistName;
}

// Category labels for descriptions
const CATEGORY_DESCRIPTORS: Record<string, string> = {
  concerts: "live",
  comedy: "comedy",
  broadway: "theater",
  sports: "game",
  misc: "event",
};

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const eventSlug = req.query.event as string;
  const userAgent = req.headers["user-agent"] || "";

  // If not a crawler, redirect to the main app with query param
  if (!isCrawler(userAgent)) {
    return res.redirect(302, `${SITE_URL}/?event=${eventSlug}`);
  }

  try {
    // Fetch events data from GitHub raw to avoid stale data after code deploys
    const eventsResponse = await fetch(
      "https://raw.githubusercontent.com/TheRyanMiller/atl-gigs/master/public/events/events.json"
    );
    if (!eventsResponse.ok) {
      return res.redirect(302, `/?event=${eventSlug}`);
    }

    const events = await eventsResponse.json();
    const event = events.find((e: any) => e.slug === eventSlug);

    if (!event) {
      return res.redirect(302, `/?event=${eventSlug}`);
    }

    // Build event-specific OG data
    const artistName = getHeadliner(event.artists?.[0]?.name || "Event");
    const venue = event.venue || "Atlanta";
    const dateShort = formatDateShort(event.date);
    const dateLong = formatDateLong(event.date);
    const categoryDescriptor = CATEGORY_DESCRIPTORS[event.category] || "live";
    // Generate dynamic OG image with overlay, fallback to default
    const ogImage = event.image_url
      ? `${SITE_URL}/api/og-image?image=${encodeURIComponent(event.image_url)}&date=${event.date}`
      : DEFAULT_OG_IMAGE;

    const title = `${artistName} @ ${venue} · ${dateShort}`;
    const description = `${dateLong} · ${artistName} ${categoryDescriptor} @ ${venue}. Get tickets and event details on ATL Gigs.`;
    const eventUrl = `${SITE_URL}?event=${event.slug}`;

    // Return minimal HTML with OG tags for crawlers
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${escapeHtml(title)}</title>
  <meta name="description" content="${escapeHtml(description)}" />

  <!-- Open Graph -->
  <meta property="og:type" content="website" />
  <meta property="og:url" content="${eventUrl}" />
  <meta property="og:title" content="${escapeHtml(title)}" />
  <meta property="og:description" content="${escapeHtml(description)}" />
  <meta property="og:image" content="${ogImage}" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:site_name" content="ATL Gigs" />

  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:url" content="${eventUrl}" />
  <meta name="twitter:title" content="${escapeHtml(title)}" />
  <meta name="twitter:description" content="${escapeHtml(description)}" />
  <meta name="twitter:image" content="${ogImage}" />

  <!-- Redirect browsers to main app -->
  <meta http-equiv="refresh" content="0;url=${SITE_URL}/?event=${event.slug}" />
</head>
<body>
  <p>Redirecting to <a href="${SITE_URL}/?event=${event.slug}">${escapeHtml(title)}</a>...</p>
</body>
</html>`;

    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.setHeader("Cache-Control", "public, max-age=3600");
    return res.status(200).send(html);
  } catch (error) {
    console.error("OG handler error:", error);
    return res.redirect(302, `/?event=${eventSlug}`);
  }
}
