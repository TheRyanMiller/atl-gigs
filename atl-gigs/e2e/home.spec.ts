import { test, expect } from "@playwright/test";

const getTodayET = () =>
  new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });


test.beforeEach(async ({ page }) => {
  const now = new Date().toISOString();
  const today = getTodayET();

  const events = [
    {
      slug: `${today}-center-stage-scott-ivey`,
      venue: "Center Stage",
      date: today,
      doors_time: "19:00",
      show_time: "20:00",
      artists: [
        { name: "Scott Ivey", spotify_url: "https://open.spotify.com/artist/AAA" },
        { name: "The Filthy Frets", spotify_url: "https://open.spotify.com/artist/BBB" },
      ],
      price: "$20",
      ticket_url: "https://example.com/tickets",
      info_url: "https://example.com/info",
      image_url: null,
      category: "concerts",
      first_seen: now,
      last_seen: now,
      is_new: true,
    },
  ];

  const status = {
    last_run: now,
    all_success: true,
    any_success: true,
    total_events: events.length,
    venues: {},
  };

  await page.route("**/scrape-status.json*", (route) =>
    route.fulfill({ json: status })
  );
  await page.route("**/events.json*", (route) =>
    route.fulfill({ json: events })
  );
});

test("loads events and opens modal", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Scott Ivey")).toBeVisible();
  await expect(page.getByLabel("Open Spotify artist").first()).toBeVisible();

  await page.getByText("Scott Ivey").click();
  await expect(page).toHaveURL(/\\?event=/);
  await expect(page.getByRole("link", { name: "Tickets" })).toBeVisible();
});
