import { useState, useMemo, useCallback } from "react";
import { FixedSizeList as List } from "react-window";
import { Event } from "../types";
import EventCard from "../components/EventCard";
import FilterBar from "../components/FilterBar";

interface HomeProps {
  events: Event[];
  onEventClick: (event: Event) => void;
}

interface DateRange {
  start: string | null;
  end: string | null;
}

const HEADER_HEIGHT = "16vh";
const LOGO_SIZE = 90; // px

export default function Home({ events, onEventClick }: HomeProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedVenues, setSelectedVenues] = useState<string[]>([]);
  const [dateRange, setDateRange] = useState<DateRange>({ start: null, end: null });

  // Get unique venues
  const venues = useMemo(() => {
    const uniqueVenues = new Set(events.map((event) => event.venue));
    return Array.from(uniqueVenues).sort();
  }, [events]);

  // Filter events based on search, venue selection, and date range
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      // Venue filter
      if (selectedVenues.length > 0 && !selectedVenues.includes(event.venue)) {
        return false;
      }

      // Date range filter
      if (dateRange.start || dateRange.end) {
        const eventDate = event.date; // Already in YYYY-MM-DD format
        if (dateRange.start && eventDate < dateRange.start) {
          return false;
        }
        if (dateRange.end && eventDate > dateRange.end) {
          return false;
        }
      }

      // Search filter
      if (searchQuery.length >= 3) {
        const query = searchQuery.toLowerCase();
        return event.artists.some((artist) =>
          artist.name.toLowerCase().includes(query)
        );
      }
      return true;
    });
  }, [events, searchQuery, selectedVenues, dateRange]);

  const handleSearchChange = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  const handleVenueToggle = useCallback((venue: string) => {
    setSelectedVenues((prev) =>
      prev.includes(venue) ? prev.filter((v) => v !== venue) : [...prev, venue]
    );
  }, []);

  const handleDateRangeChange = useCallback((range: DateRange) => {
    setDateRange(range);
  }, []);

  const Row = ({
    index,
    style,
  }: {
    index: number;
    style: React.CSSProperties;
  }) => {
    const event = filteredEvents[index];
    return (
      <div style={style} className="box-border w-full">
        <EventCard event={event} onClick={() => onEventClick(event)} />
      </div>
    );
  };

  return (
    <div className="min-h-screen w-full bg-gray-50 dark:bg-zinc-900 overflow-x-hidden">
      {/* Header with Logo */}
      <div
        className="w-full flex flex-col items-center justify-end pb-4 pt-6 sticky top-0 z-40 bg-gradient-to-b from-gray-50 via-gray-50 to-gray-50/95 dark:from-zinc-900 dark:via-zinc-900 dark:to-zinc-900/95"
        style={{ minHeight: HEADER_HEIGHT }}
      >
        <div
          style={{
            width: LOGO_SIZE,
            height: LOGO_SIZE,
            aspectRatio: "1/1",
          }}
        >
          <img
            src="/atlgigs.png"
            alt="ATL Gigs Logo"
            className="w-full h-full object-contain drop-shadow-sm"
          />
        </div>
      </div>
      <div className="max-w-[90vw] mx-auto w-full pt-4">
        <FilterBar
          venues={venues}
          selectedVenues={selectedVenues}
          onVenueToggle={handleVenueToggle}
          onSearchChange={handleSearchChange}
          onDateRangeChange={handleDateRangeChange}
        />
        <div className="mt-8 w-full">
          {filteredEvents.length > 0 ? (
            <List
              height={filteredEvents.length * 240}
              itemCount={filteredEvents.length}
              itemSize={240}
              width={"100%"}
              className="w-full"
            >
              {Row}
            </List>
          ) : (
            <div className="text-center text-gray-500 dark:text-zinc-400 py-12">
              No events found matching your criteria
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
