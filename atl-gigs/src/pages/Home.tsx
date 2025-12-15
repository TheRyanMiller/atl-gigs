import { useState, useMemo, useCallback, useEffect, useRef, forwardRef } from "react";
import { VariableSizeList as List } from "react-window";
import AutoSizer from "react-virtualized-auto-sizer";
import { Music, Loader2 } from "lucide-react";
import { Event, EventCategory, ALL_CATEGORIES } from "../types";
import EventCard from "../components/EventCard";
import FilterBar from "../components/FilterBar";

interface HomeProps {
  events: Event[];
  loading: boolean;
  onEventClick: (event: Event) => void;
}

interface DateRange {
  start: string | null;
  end: string | null;
}

// Get today's date in YYYY-MM-DD format for comparison (US Eastern timezone)
const getTodayString = () => {
  const now = new Date();
  // Format in Eastern time to get the current date in Atlanta
  const eastern = now.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
  return eastern; // Returns YYYY-MM-DD format
};

// Calculate mobile card height based on content
const getMobileCardHeight = (event: Event): number => {
  // Image section: h-[147px]
  let height = 147;

  // Content container padding: p-4 (16px) top, pb-3 (12px) bottom
  height += 16 + 12;

  // Title: text-lg leading-snug, assume 2 lines max (~50px)
  height += 50;

  // Title container margin bottom: mb-2.5 = 10px
  height += 10;

  // Support artists (if present): mt-2 (8px) + text-sm (~20px) = 28px
  if (event.artists.length > 1) {
    height += 28;
  }

  // Details section with space-y-1.5 (6px gaps between items)
  // Venue: always present (~20px)
  height += 20;
  // Date: always present (6px gap + 20px)
  height += 6 + 20;
  // Doors (if present): 6px gap + 20px
  if (event.doors_time) {
    height += 6 + 20;
  }
  // Price (if present): 6px gap + 20px
  if (event.price) {
    height += 6 + 20;
  }

  // Gap between text block and action area: gap-4 = 16px
  height += 16;

  // Action buttons: h-10 = 40px
  height += 40;

  // Safety buffer for rounding/browser differences
  height += 4;

  return height;
};

// Row heights for virtualized list
const getItemHeight = (event: Event, isMobile: boolean): number => {
  // Desktop: fixed 195px + 16px gap
  // Mobile: dynamic based on content + 16px gap
  return isMobile ? getMobileCardHeight(event) + 16 : 211;
};

// Inner element wrapper to add top padding for buffer above first card
const innerElementType = forwardRef<HTMLDivElement, React.HTMLProps<HTMLDivElement>>(
  ({ style, ...rest }, ref) => (
    <div
      ref={ref}
      style={{ ...style, paddingTop: 16 }}
      {...rest}
    />
  )
);

export default function Home({ events, loading, onEventClick }: HomeProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedVenues, setSelectedVenues] = useState<string[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<EventCategory[]>([]);
  const [dateRange, setDateRange] = useState<DateRange>({ start: null, end: null });
  const [showOnlyNew, setShowOnlyNew] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const listRef = useRef<List>(null);

  // Check if mobile on mount and resize
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 640);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Get unique venues
  const venues = useMemo(() => {
    const uniqueVenues = new Set(events.map((event) => event.venue));
    return Array.from(uniqueVenues).sort();
  }, [events]);

  // Get categories that exist in events
  const categories = useMemo(() => {
    const eventCategories = new Set(events.map((event) => event.category));
    return ALL_CATEGORIES.filter((cat) => eventCategories.has(cat));
  }, [events]);

  // Filter events based on search, category, venue selection, and date range
  const filteredEvents = useMemo(() => {
    const today = getTodayString();
    const now = new Date();
    const staleThresholdMs = 3 * 24 * 60 * 60 * 1000; // 3 days in milliseconds

    return events.filter((event) => {
      // Hide stale events (not seen by scraper in > 3 days) - likely cancelled
      if (event.last_seen) {
        const lastSeenDate = new Date(event.last_seen);
        const daysSinceLastSeen = now.getTime() - lastSeenDate.getTime();
        if (daysSinceLastSeen > staleThresholdMs) {
          return false;
        }
      }

      // Default to today onwards when no start date is set
      // (Past events require explicit start date selection)
      if (!dateRange.start && event.date < today) {
        return false;
      }

      // Explicit date range filtering
      if (dateRange.start && event.date < dateRange.start) {
        return false;
      }
      if (dateRange.end && event.date > dateRange.end) {
        return false;
      }

      // Category filter
      if (selectedCategories.length > 0 && !selectedCategories.includes(event.category)) {
        return false;
      }

      // Venue filter
      if (selectedVenues.length > 0 && !selectedVenues.includes(event.venue)) {
        return false;
      }

      // New filter - show only newly added events
      if (showOnlyNew && !event.is_new) {
        return false;
      }

      // Search filter
      if (searchQuery.length >= 3) {
        const query = searchQuery.toLowerCase();
        const artistMatch = event.artists.some((artist) =>
          artist.name.toLowerCase().includes(query)
        );
        const venueMatch = event.venue.toLowerCase().includes(query);
        return artistMatch || venueMatch;
      }
      return true;
    });
  }, [events, searchQuery, selectedCategories, selectedVenues, dateRange, showOnlyNew]);

  // Reset list scroll when filters change
  useEffect(() => {
    listRef.current?.scrollTo(0);
  }, [searchQuery, selectedCategories, selectedVenues, dateRange, showOnlyNew]);

  // Reset list cache when filtered events or mobile state changes
  useEffect(() => {
    listRef.current?.resetAfterIndex(0);
  }, [filteredEvents, isMobile]);

  const handleSearchChange = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  const handleCategoryToggle = useCallback((category: EventCategory) => {
    setSelectedCategories((prev) =>
      prev.includes(category) ? prev.filter((c) => c !== category) : [...prev, category]
    );
  }, []);

  const handleVenueToggle = useCallback((venue: string) => {
    setSelectedVenues((prev) =>
      prev.includes(venue) ? prev.filter((v) => v !== venue) : [...prev, venue]
    );
  }, []);

  const handleDateRangeChange = useCallback((range: DateRange) => {
    setDateRange(range);
  }, []);

  const handleShowOnlyNewToggle = useCallback(() => {
    setShowOnlyNew((prev) => !prev);
  }, []);

  // Get item size for virtualized list
  const getItemSize = useCallback(
    (index: number) => {
      const event = filteredEvents[index];
      return getItemHeight(event, isMobile); // Already includes gap
    },
    [filteredEvents, isMobile]
  );

  // Row renderer for virtualized list
  const Row = useCallback(
    ({ index, style }: { index: number; style: React.CSSProperties }) => {
      const event = filteredEvents[index];
      // Calculate the card height (row height minus gap)
      const cardHeight = isMobile ? getMobileCardHeight(event) : 195;
      return (
        <div style={{ ...style, paddingBottom: 16 }}>
          <EventCard
            key={event.slug}
            event={event}
            onClick={() => onEventClick(event)}
            mobileHeight={isMobile ? cardHeight : undefined}
          />
        </div>
      );
    },
    [filteredEvents, onEventClick, isMobile]
  );

  return (
    <div className="h-[calc(100dvh-56px)] sm:h-[calc(100dvh-80px)] flex flex-col">
      {/* Search & Filters */}
      <div className="shrink-0 bg-neutral-950 pb-2 border-b border-white/10 overflow-visible">
        <div className="max-w-5xl mx-auto w-full px-4 overflow-visible">
          <FilterBar
            venues={venues}
            selectedVenues={selectedVenues}
            onVenueToggle={handleVenueToggle}
            categories={categories}
            selectedCategories={selectedCategories}
            onCategoryToggle={handleCategoryToggle}
            onSearchChange={handleSearchChange}
            onDateRangeChange={handleDateRangeChange}
            showOnlyNew={showOnlyNew}
            onShowOnlyNewToggle={handleShowOnlyNewToggle}
          />
        </div>
      </div>

      {/* Events List - Virtualized */}
      <div className="flex-1 min-h-0 max-w-5xl mx-auto w-full px-4">
        {loading && (
          <div className="text-center py-20">
            <Loader2 size={48} className="mx-auto text-teal-500 animate-spin" />
          </div>
        )}

        {!loading && filteredEvents.length === 0 && (
          <div className="text-center py-20 bg-neutral-900/30 rounded-3xl border border-neutral-800 border-dashed">
            <Music size={48} className="mx-auto text-neutral-700 mb-4" />
            <h3 className="text-xl font-bold text-white">No gigs found</h3>
            <p className="text-neutral-500 mt-2">Try adjusting your search terms</p>
          </div>
        )}

        {!loading && filteredEvents.length > 0 && (
          <AutoSizer>
            {({ height, width }) => (
              <List
                ref={listRef}
                height={height}
                width={width}
                itemCount={filteredEvents.length}
                itemSize={getItemSize}
                overscanCount={3}
                innerElementType={innerElementType}
              >
                {Row}
              </List>
            )}
          </AutoSizer>
        )}
      </div>
    </div>
  );
}
