import { useState, useMemo, useCallback, useEffect } from "react";
import { Music, Loader2 } from "lucide-react";
import { Event, EventCategory, ALL_CATEGORIES } from "../types";
import EventCard from "../components/EventCard";
import FilterBar from "../components/FilterBar";
import { useArchive } from "../hooks/useArchive";

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

export default function Home({ events, loading, onEventClick }: HomeProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedVenues, setSelectedVenues] = useState<string[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<EventCategory[]>([]);
  const [dateRange, setDateRange] = useState<DateRange>({ start: null, end: null });

  // Archive hook for loading past events
  const { archiveEvents, loadMonthsForRange } = useArchive();

  // Load archive events when date range includes past dates
  useEffect(() => {
    const today = getTodayString();
    if (dateRange.start && dateRange.start < today) {
      loadMonthsForRange(dateRange.start, dateRange.end);
    }
  }, [dateRange.start, dateRange.end, loadMonthsForRange]);

  // Combine events with archive when date range includes past dates
  const allEvents = useMemo(() => {
    const today = getTodayString();
    // Only merge archives if user selected a past start date
    if (!dateRange.start || dateRange.start >= today) {
      return events;
    }
    // Merge and deduplicate by slug
    const slugs = new Set(events.map((e) => e.slug));
    const uniqueArchive = archiveEvents.filter((e) => !slugs.has(e.slug));
    return [...events, ...uniqueArchive];
  }, [events, archiveEvents, dateRange.start]);

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
    return allEvents.filter((event) => {
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
  }, [allEvents, searchQuery, selectedCategories, selectedVenues, dateRange]);

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
      <div className="space-y-4 max-w-6xl mx-auto">
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
