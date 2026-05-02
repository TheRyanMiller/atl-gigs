# Live Nation Venues Scraper

## Scraping Approach

Both venues use the same Live Nation GraphQL API at `https://api.livenation.com/graphql`. The scraper uses a shared function `scrape_live_nation_venue()` with venue-specific IDs:

| Venue | Venue ID |
|-------|----------|
| Tabernacle | `KovZpaFEZe` |
| Coca-Cola Roxy | `KovZ917ACc7` |

### API Details

- **Endpoint**: `https://api.livenation.com/graphql`
- **Pagination**: 36 events per page, offset-based
- **Rate limiting**: 0.4s delay between requests
- **Timeouts**: split connect/read timeout, currently `(8, 20)`

Top-level GraphQL `errors` are treated as scraper failures instead of empty event lists.

## Category Mapping

Categories are determined automatically from artist `genre` field in the API response.

### Genre → Category Mapping

| API Genre Contains | Our Category |
|--------------------|--------------|
| comedy, stand-up, standup, comedian | `comedy` |
| theatre, theater, broadway, musical | `broadway` |
| (default) | `concerts` |

### Examples
- John Mulaney (genre: "Stand-up") → `comedy`
- Most musical acts → `concerts` (default)

## Edge Cases

### Multiple Artists
The headliner's genre determines the category. If no headliner genre matches comedy/broadway keywords, defaults to `concerts`.

### Missing Genre Data
Some artists may not have genre data in the API. These events default to `concerts`.

### Time Semantics
`event_time` is treated as `show_time`. The API often returns `event_end_time: null`, and no separate doors field is currently exposed by this query, so `doors_time` remains `None`.

### Shared Infrastructure
Both Tabernacle and Coca-Cola Roxy use the same scraper logic. Changes to category mapping affect both venues.

## Notes

- API requires specific headers including `x-api-key`
- Events are sorted by start date ascending
- Cancelled and postponed events are excluded via API filter
- Image URL uses `RETINA_PORTRAIT_16_9` identifier for consistent sizing
