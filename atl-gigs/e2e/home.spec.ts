import { test, expect } from "@playwright/test";

const getTodayET = () =>
  new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });

const longDescription = "A detailed artist biography for this show. ".repeat(30);
const testImage =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 9'%3E%3Crect width='16' height='9' fill='%230f766e'/%3E%3C/svg%3E";

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
      image_url: testImage,
      description: longDescription,
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
  await expect(page.getByText("A detailed artist biography for this show.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Tickets" })).toBeVisible();
});

test("expanding long descriptions does not resize modal image", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/");

  await page.getByText("Scott Ivey").click();
  const modalImage = page.getByRole("img", { name: "Scott Ivey" }).last();
  await expect(page.getByText("Show more")).toBeVisible();

  const before = await modalImage.boundingBox();
  await page.getByText("Show more").click();
  const after = await modalImage.boundingBox();

  expect(before?.height).toBeGreaterThan(0);
  expect(after?.height).toBe(before?.height);
});

test("long description expansion is reachable on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  await page.getByText("Scott Ivey").click();
  const scrollArea = page.getByTestId("event-modal-scroll-area");
  const showMore = page.getByRole("button", { name: "Show more" });
  await expect(scrollArea).toBeVisible();

  await scrollArea.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });

  await expect(showMore).toBeVisible();
  const buttonBox = await showMore.boundingBox();
  const viewport = page.viewportSize();

  expect(buttonBox).not.toBeNull();
  expect(viewport).not.toBeNull();
  expect(buttonBox!.y).toBeGreaterThanOrEqual(0);
  expect(buttonBox!.y + buttonBox!.height).toBeLessThanOrEqual(viewport!.height);

  await showMore.click();
  await expect(page.getByRole("button", { name: "Show less" })).toBeVisible();
});
