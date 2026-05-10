# The Punchline Scraper

## Scraping Approach
- Uses the public XML webservice loaded by `https://www.punchline.com/shows/`.
- Event list request: `POST https://webservice.punchline.com/` with `entity=event`, public site token, `variable2` page size, and `variable3` offset.
- Showtimes request: `entity=show`, `variable1={eventid}`.
- Each returned showtime becomes one ATL Gigs event because ticket URLs include both `eventid` and `showid`.

## Category Mapping
- All Punchline events map to `comedy`.

## Edge Cases
- The WordPress Events Calendar REST API is present but currently returns no real show inventory.
- Event records can cover date ranges; the scraper expands those through the `show` endpoint instead of using the range.
- Direct ticket URLs use `/f1-sections/?type=new&eventid={eventid}&showid={showtimeid}`.
- Some upstream descriptions contain placeholder link markers and replacement characters; the scraper removes those before storing descriptions.

## Opinionated Decisions
- `doors_time` is left empty because the site only documents general door policies, not per-show door times.
- Base ticket price from the XML `price` field is stored instead of calculating tax, handling, or VIP totals.
