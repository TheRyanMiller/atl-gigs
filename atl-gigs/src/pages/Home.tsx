import { useState, useMemo, useCallback } from "react";
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

export default function Home({ events, loading, onEventClick }: HomeProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedVenues, setSelectedVenues] = useState<string[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<EventCategory[]>([]);
  const [dateRange, setDateRange] = useState<DateRange>({ start: null, end: null });

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

  // Get today's date in YYYY-MM-DD format for comparison (local timezone)
  const getTodayString = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  // Filter events based on search, category, venue selection, and date range
  const filteredEvents = useMemo(() => {
    const today = getTodayString();
    return events.filter((event) => {
      // Filter out past events (before today)
      if (event.date < today) {
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

      // Date range filter
      if (dateRange.start || dateRange.end) {
        const eventDate = event.date;
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
        const artistMatch = event.artists.some((artist) =>
          artist.name.toLowerCase().includes(query)
        );
        const venueMatch = event.venue.toLowerCase().includes(query);
        return artistMatch || venueMatch;
      }
      return true;
    });
  }, [events, searchQuery, selectedCategories, selectedVenues, dateRange]);

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

  return (
    <div className="space-y-6">
      {/* Search & Filters */}
      <FilterBar
        venues={venues}
        selectedVenues={selectedVenues}
        onVenueToggle={handleVenueToggle}
        categories={categories}
        selectedCategories={selectedCategories}
        onCategoryToggle={handleCategoryToggle}
        onSearchChange={handleSearchChange}
        onDateRangeChange={handleDateRangeChange}
      />

      {/* Events List */}
      <div className="space-y-4">
        {filteredEvents.map((event, index) => (
          <EventCard
            key={`${event.venue}-${event.date}-${index}`}
            event={event}
            onClick={() => onEventClick(event)}
          />
        ))}

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
      </div>
    </div>
  );
}
