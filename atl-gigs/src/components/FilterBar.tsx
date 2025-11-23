import { useState, useEffect, useRef } from "react";
import { format } from "date-fns";

interface DateRange {
  start: string | null;
  end: string | null;
}

interface FilterBarProps {
  venues: string[];
  selectedVenues: string[];
  onVenueToggle: (venue: string) => void;
  onSearchChange: (query: string) => void;
  onDateRangeChange: (range: DateRange) => void;
}

export default function FilterBar({
  venues,
  selectedVenues,
  onVenueToggle,
  onSearchChange,
  onDateRangeChange,
}: FilterBarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [venueDropdownOpen, setVenueDropdownOpen] = useState(false);
  const [dateDropdownOpen, setDateDropdownOpen] = useState(false);
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const venueDropdownRef = useRef<HTMLDivElement>(null);
  const dateDropdownRef = useRef<HTMLDivElement>(null);

  // Get today's date in YYYY-MM-DD format for min attribute
  const today = format(new Date(), "yyyy-MM-dd");

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    onSearchChange(debouncedQuery);
  }, [debouncedQuery, onSearchChange]);

  // Notify parent of date range changes
  useEffect(() => {
    onDateRangeChange({
      start: startDate || null,
      end: endDate || null,
    });
  }, [startDate, endDate, onDateRangeChange]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        venueDropdownRef.current &&
        !venueDropdownRef.current.contains(event.target as Node)
      ) {
        setVenueDropdownOpen(false);
      }
      if (
        dateDropdownRef.current &&
        !dateDropdownRef.current.contains(event.target as Node)
      ) {
        setDateDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const clearDateFilter = () => {
    setStartDate("");
    setEndDate("");
  };

  const getDateLabel = () => {
    if (startDate && endDate) {
      if (startDate === endDate) {
        return format(new Date(startDate), "MMM d");
      }
      return `${format(new Date(startDate), "MMM d")} - ${format(new Date(endDate), "MMM d")}`;
    }
    if (startDate) {
      return `From ${format(new Date(startDate), "MMM d")}`;
    }
    if (endDate) {
      return `Until ${format(new Date(endDate), "MMM d")}`;
    }
    return "Any date";
  };

  const hasDateFilter = startDate || endDate;

  return (
    <div className="sticky top-0 z-10 bg-white/80 dark:bg-zinc-800/80 backdrop-blur-md shadow-[0_2px_8px_rgba(0,0,0,0.06)] dark:shadow-[0_2px_8px_rgba(0,0,0,0.2)] p-4 rounded-xl border border-gray-100 dark:border-zinc-700/50">
      <div className="flex flex-col md:flex-row gap-3">
        {/* Search input */}
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search artists..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2.5 border border-gray-200 dark:border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-gray-50 dark:bg-zinc-700 text-gray-900 dark:text-zinc-100 placeholder-gray-400 dark:placeholder-zinc-400 transition-all duration-200"
          />
        </div>

        {/* Venue filter */}
        <div className="relative w-full md:w-48" ref={venueDropdownRef}>
          <button
            type="button"
            className="w-full px-4 py-2.5 border border-gray-200 dark:border-zinc-600 rounded-lg bg-gray-50 dark:bg-zinc-700 text-left focus:outline-none focus:ring-2 focus:ring-purple-500 text-gray-700 dark:text-zinc-200 transition-all duration-200 flex items-center justify-between"
            onClick={() => setVenueDropdownOpen((open) => !open)}
          >
            <span className="truncate text-sm">
              {selectedVenues.length > 0
                ? `${selectedVenues.length} venue${selectedVenues.length > 1 ? "s" : ""}`
                : "All venues"}
            </span>
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform duration-200 flex-shrink-0 ml-2 ${venueDropdownOpen ? "rotate-180" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
          {venueDropdownOpen && (
            <div className="absolute mt-2 w-full bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-600 rounded-xl shadow-lg z-20 max-h-60 overflow-auto">
              <div className="p-2">
                {venues.map((venue) => (
                  <label
                    key={venue}
                    className="flex items-center py-2 px-2 cursor-pointer text-gray-700 dark:text-zinc-200 hover:bg-gray-50 dark:hover:bg-zinc-700 rounded-lg transition-colors duration-150"
                  >
                    <input
                      type="checkbox"
                      checked={selectedVenues.includes(venue)}
                      onChange={() => onVenueToggle(venue)}
                      className="mr-3 w-4 h-4 accent-purple-600 rounded"
                    />
                    <span className="text-sm">{venue}</span>
                  </label>
                ))}
                {venues.length === 0 && (
                  <div className="text-gray-400 text-sm p-2">
                    No venues available
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Date range filter */}
        <div className="relative w-full md:w-48" ref={dateDropdownRef}>
          <button
            type="button"
            className={`w-full px-4 py-2.5 border rounded-lg bg-gray-50 dark:bg-zinc-700 text-left focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all duration-200 flex items-center justify-between ${
              hasDateFilter
                ? "border-purple-300 dark:border-purple-600"
                : "border-gray-200 dark:border-zinc-600"
            }`}
            onClick={() => setDateDropdownOpen((open) => !open)}
          >
            <span className="truncate text-sm text-gray-700 dark:text-zinc-200">
              {getDateLabel()}
            </span>
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform duration-200 flex-shrink-0 ml-2 ${dateDropdownOpen ? "rotate-180" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
          {dateDropdownOpen && (
            <div className="absolute mt-2 w-64 bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-600 rounded-xl shadow-lg z-20 p-4">
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-zinc-400 mb-1">
                    From
                  </label>
                  <input
                    type="date"
                    value={startDate}
                    min={today}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-zinc-600 rounded-lg bg-gray-50 dark:bg-zinc-700 text-gray-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-zinc-400 mb-1">
                    To
                  </label>
                  <input
                    type="date"
                    value={endDate}
                    min={startDate || today}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 dark:border-zinc-600 rounded-lg bg-gray-50 dark:bg-zinc-700 text-gray-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                {hasDateFilter && (
                  <button
                    type="button"
                    onClick={clearDateFilter}
                    className="w-full text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 transition-colors py-1"
                  >
                    Clear dates
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
