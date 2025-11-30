import { useState, useEffect, useRef } from "react";
import { format } from "date-fns";
import { Search, MapPin, Calendar, X, ChevronDown, Tag } from "lucide-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faGuitar, faFaceLaughSquint, faMasksTheater, faFootball, faStar } from "@fortawesome/free-solid-svg-icons";
import { EventCategory, CATEGORY_LABELS } from "../types";

const categoryIcons = {
  concerts: faGuitar,
  comedy: faFaceLaughSquint,
  broadway: faMasksTheater,
  sports: faFootball,
  misc: faStar,
};

interface DateRange {
  start: string | null;
  end: string | null;
}

interface FilterBarProps {
  venues: string[];
  selectedVenues: string[];
  onVenueToggle: (venue: string) => void;
  categories: EventCategory[];
  selectedCategories: EventCategory[];
  onCategoryToggle: (category: EventCategory) => void;
  onSearchChange: (query: string) => void;
  onDateRangeChange: (range: DateRange) => void;
}

const FilterPill = ({
  label,
  active = false,
  icon: Icon,
  onClick,
  onClear,
}: {
  label: string;
  active?: boolean;
  icon: React.ElementType;
  onClick: (e: React.MouseEvent) => void;
  onClear?: (e: React.MouseEvent) => void;
}) => (
  <button
    onClick={onClick}
    className={`
      flex items-center gap-2 px-3 py-3 rounded-xl text-sm font-medium transition-all
      border backdrop-blur-sm whitespace-nowrap h-full
      ${
        active
          ? "bg-teal-500/10 border-teal-500/50 text-teal-300"
          : "bg-neutral-900/50 border-neutral-800 text-neutral-400 hover:bg-neutral-800 hover:text-white"
      }
    `}
  >
    <Icon size={14} />
    <span>{label}</span>
    {active && onClear ? (
      <span
        onClick={onClear}
        className="p-0.5 rounded-full hover:bg-neutral-700 transition-colors"
      >
        <X size={12} />
      </span>
    ) : (
      <ChevronDown size={12} className="opacity-50" />
    )}
  </button>
);

export default function FilterBar({
  venues,
  selectedVenues,
  onVenueToggle,
  categories,
  selectedCategories,
  onCategoryToggle,
  onSearchChange,
  onDateRangeChange,
}: FilterBarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [venueDropdownOpen, setVenueDropdownOpen] = useState(false);
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false);
  const [dateDropdownOpen, setDateDropdownOpen] = useState(false);
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const venueDropdownRef = useRef<HTMLDivElement>(null);
  const categoryDropdownRef = useRef<HTMLDivElement>(null);
  const dateDropdownRef = useRef<HTMLDivElement>(null);
  const mobileVenueDropdownRef = useRef<HTMLDivElement>(null);
  const mobileCategoryDropdownRef = useRef<HTMLDivElement>(null);
  const mobileDateDropdownRef = useRef<HTMLDivElement>(null);

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
    function handleClickOutside(event: MouseEvent | TouchEvent) {
      const target = event.target as Node;
      const isInsideVenue =
        venueDropdownRef.current?.contains(target) ||
        mobileVenueDropdownRef.current?.contains(target);
      const isInsideCategory =
        categoryDropdownRef.current?.contains(target) ||
        mobileCategoryDropdownRef.current?.contains(target);
      const isInsideDate =
        dateDropdownRef.current?.contains(target) ||
        mobileDateDropdownRef.current?.contains(target);

      if (!isInsideVenue) {
        setVenueDropdownOpen(false);
      }
      if (!isInsideCategory) {
        setCategoryDropdownOpen(false);
      }
      if (!isInsideDate) {
        setDateDropdownOpen(false);
      }
    }
    
    // Use mousedown for desktop (immediate)
    document.addEventListener("mousedown", handleClickOutside);
    
    // Use touchend for mobile (after touch completes) to prevent click-through
    document.addEventListener("touchend", handleClickOutside);
    
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchend", handleClickOutside);
    };
  }, []);

  const clearDateFilter = (e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    setStartDate("");
    setEndDate("");
  };

  const clearVenueFilter = (e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    selectedVenues.forEach((v) => onVenueToggle(v));
  };

  const getDateLabel = () => {
    if (startDate && endDate) {
      if (startDate === endDate) {
        return format(new Date(startDate), "MMM d");
      }
      return `${format(new Date(startDate), "MMM d")} - ${format(
        new Date(endDate),
        "MMM d"
      )}`;
    }
    if (startDate) {
      return `From ${format(new Date(startDate), "MMM d")}`;
    }
    if (endDate) {
      return `Until ${format(new Date(endDate), "MMM d")}`;
    }
    return "Any Date";
  };

  const getVenueLabel = () => {
    if (selectedVenues.length === 0) return "Venues";
    if (selectedVenues.length === 1) return selectedVenues[0];
    return `${selectedVenues.length} Venues`;
  };

  const getCategoryLabel = () => {
    if (selectedCategories.length === 0) return "Categories";
    if (selectedCategories.length === 1) return CATEGORY_LABELS[selectedCategories[0]];
    return `${selectedCategories.length} Categories`;
  };

  const clearCategoryFilter = (e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    selectedCategories.forEach((c) => onCategoryToggle(c));
  };

  const hasDateFilter = !!(startDate || endDate);
  const hasVenueFilter = selectedVenues.length > 0;
  const hasCategoryFilter = selectedCategories.length > 0;

  return (
    <div className="space-y-4">
      {/* Search and Filter Row */}
      <div className="flex flex-col md:flex-row gap-4">
        {/* Search Input */}
        <div className="relative flex-1 group">
          <Search
            className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-500 group-focus-within:text-teal-500 transition-colors"
            size={20}
          />
          <input
            type="text"
            placeholder="Search artists, venues, etc..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-neutral-900/50 border border-neutral-800 rounded-2xl py-4 pl-12 pr-12 text-white placeholder:text-neutral-600 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-transparent transition-all shadow-sm"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-white transition-colors"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Desktop Filter Pills */}
        <div className="hidden md:flex items-stretch gap-3">
          {/* Category Filter */}
          <div className="relative" ref={categoryDropdownRef}>
            <FilterPill
              label={getCategoryLabel()}
              active={hasCategoryFilter}
              icon={Tag}
              onClick={(e) => {
                e.stopPropagation();
                setCategoryDropdownOpen((open) => !open);
                setVenueDropdownOpen(false);
                setDateDropdownOpen(false);
              }}
              onClear={clearCategoryFilter}
            />
            {categoryDropdownOpen && (
              <div 
                className="absolute mt-2 bg-neutral-900 border border-neutral-800 rounded-xl shadow-xl z-20 p-2"
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex flex-wrap gap-1.5">
                  {categories.map((category) => (
                    <button
                      key={category}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onCategoryToggle(category);
                      }}
                      className={`
                        flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition-all select-none
                        ${selectedCategories.includes(category)
                          ? "bg-teal-500/20 text-teal-300 border border-teal-500/50"
                          : "bg-neutral-800 text-neutral-400 border border-neutral-700 hover:bg-neutral-700 hover:text-white"
                        }
                      `}
                    >
                      <FontAwesomeIcon icon={categoryIcons[category]} className="w-3 h-3" />
                      {CATEGORY_LABELS[category]}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Venue Filter */}
          <div className="relative" ref={venueDropdownRef}>
            <FilterPill
              label={getVenueLabel()}
              active={hasVenueFilter}
              icon={MapPin}
              onClick={(e) => {
                e.stopPropagation();
                setVenueDropdownOpen((open) => !open);
                setCategoryDropdownOpen(false);
                setDateDropdownOpen(false);
              }}
              onClear={clearVenueFilter}
            />
            {venueDropdownOpen && (
              <div 
                className="absolute mt-2 bg-neutral-900 border border-neutral-800 rounded-xl shadow-xl z-20 p-2 right-0"
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex flex-col gap-1.5">
                  {venues.map((venue) => (
                    <button
                      key={venue}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onVenueToggle(venue);
                      }}
                      className={`
                        px-2 py-1 rounded-md text-xs font-medium transition-all whitespace-nowrap text-left select-none
                        ${selectedVenues.includes(venue)
                          ? "bg-teal-500/20 text-teal-300 border border-teal-500/50"
                          : "bg-neutral-800 text-neutral-400 border border-neutral-700 hover:bg-neutral-700 hover:text-white"
                        }
                      `}
                    >
                      {venue}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Date Filter */}
          <div className="relative" ref={dateDropdownRef}>
            <FilterPill
              label={getDateLabel()}
              active={hasDateFilter}
              icon={Calendar}
              onClick={(e) => {
                e.stopPropagation();
                setDateDropdownOpen((open) => !open);
                setCategoryDropdownOpen(false);
                setVenueDropdownOpen(false);
              }}
              onClear={clearDateFilter}
            />
            {dateDropdownOpen && (
              <div 
                className="absolute mt-2 w-64 bg-neutral-900 border border-neutral-800 rounded-xl shadow-xl z-20 p-4"
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => e.stopPropagation()}
              >
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-neutral-500 mb-1">
                      From
                    </label>
                    <input
                      type="date"
                      value={startDate}
                      min={today}
                      onChange={(e) => setStartDate(e.target.value)}
                      style={{ colorScheme: 'dark' }}
                      className="w-full px-3 py-2 border border-neutral-700 rounded-lg bg-neutral-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-neutral-500 mb-1">
                      To
                    </label>
                    <input
                      type="date"
                      value={endDate}
                      min={startDate || today}
                      onChange={(e) => setEndDate(e.target.value)}
                      style={{ colorScheme: 'dark' }}
                      className="w-full px-3 py-2 border border-neutral-700 rounded-lg bg-neutral-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    />
                  </div>
                  {hasDateFilter && (
                    <button
                      type="button"
                      onClick={clearDateFilter}
                      className="w-full text-sm text-teal-400 hover:text-teal-300 transition-colors py-1"
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

      {/* Mobile Filter Pills */}
      <div className="md:hidden space-y-3">
        {/* Filter Buttons Row */}
        <div className="flex gap-3 pb-2 overflow-x-auto">
          <div ref={mobileCategoryDropdownRef}>
            <FilterPill
              label={getCategoryLabel()}
              active={hasCategoryFilter}
              icon={Tag}
              onClick={(e) => {
                e.stopPropagation();
                setCategoryDropdownOpen((open) => !open);
                setVenueDropdownOpen(false);
                setDateDropdownOpen(false);
              }}
              onClear={clearCategoryFilter}
            />
          </div>
          <div ref={mobileVenueDropdownRef}>
            <FilterPill
              label={getVenueLabel()}
              active={hasVenueFilter}
              icon={MapPin}
              onClick={(e) => {
                e.stopPropagation();
                setVenueDropdownOpen((open) => !open);
                setCategoryDropdownOpen(false);
                setDateDropdownOpen(false);
              }}
              onClear={clearVenueFilter}
            />
          </div>
          <div ref={mobileDateDropdownRef}>
            <FilterPill
              label={getDateLabel()}
              active={hasDateFilter}
              icon={Calendar}
              onClick={(e) => {
                e.stopPropagation();
                setDateDropdownOpen((open) => !open);
                setCategoryDropdownOpen(false);
                setVenueDropdownOpen(false);
              }}
              onClear={clearDateFilter}
            />
          </div>
        </div>

        {/* Dropdown Content - Renders below buttons, pushes content down */}
        {categoryDropdownOpen && (
          <div 
            className="bg-neutral-900 border border-neutral-800 rounded-xl shadow-xl p-2 z-50"
            onMouseDown={(e) => e.stopPropagation()}
            onTouchStart={(e) => e.stopPropagation()}
            onTouchEnd={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex flex-wrap gap-1.5">
              {categories.map((category) => (
                <button
                  key={category}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onCategoryToggle(category);
                  }}
                  onTouchEnd={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onCategoryToggle(category);
                  }}
                  className={`
                    flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition-all select-none
                    ${selectedCategories.includes(category)
                      ? "bg-teal-500/20 text-teal-300 border border-teal-500/50"
                      : "bg-neutral-800 text-neutral-400 border border-neutral-700 hover:bg-neutral-700 hover:text-white active:bg-neutral-600"
                    }
                  `}
                >
                  <FontAwesomeIcon icon={categoryIcons[category]} className="w-3 h-3" />
                  {CATEGORY_LABELS[category]}
                </button>
              ))}
            </div>
          </div>
        )}

        {venueDropdownOpen && (
          <div 
            className="bg-neutral-900 border border-neutral-800 rounded-xl shadow-xl p-2 z-50"
            onMouseDown={(e) => e.stopPropagation()}
            onTouchStart={(e) => e.stopPropagation()}
            onTouchEnd={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex flex-wrap gap-1.5">
              {venues.map((venue) => (
                <button
                  key={venue}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onVenueToggle(venue);
                  }}
                  onTouchEnd={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onVenueToggle(venue);
                  }}
                  className={`
                    px-2 py-1 rounded-md text-xs font-medium transition-all select-none
                    ${selectedVenues.includes(venue)
                      ? "bg-teal-500/20 text-teal-300 border border-teal-500/50"
                      : "bg-neutral-800 text-neutral-400 border border-neutral-700 hover:bg-neutral-700 hover:text-white active:bg-neutral-600"
                    }
                  `}
                >
                  {venue}
                </button>
              ))}
            </div>
          </div>
        )}

        {dateDropdownOpen && (
          <div 
            className="bg-neutral-900 border border-neutral-800 rounded-xl shadow-xl p-4 z-50"
            onMouseDown={(e) => e.stopPropagation()}
            onTouchStart={(e) => e.stopPropagation()}
            onTouchEnd={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1">
                  From
                </label>
                <input
                  type="date"
                  value={startDate}
                  min={today}
                  onChange={(e) => setStartDate(e.target.value)}
                  style={{ colorScheme: 'dark' }}
                  className="w-full px-3 py-2 border border-neutral-700 rounded-lg bg-neutral-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 appearance-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1">
                  To
                </label>
                <input
                  type="date"
                  value={endDate}
                  min={startDate || today}
                  onChange={(e) => setEndDate(e.target.value)}
                  style={{ colorScheme: 'dark' }}
                  className="w-full px-3 py-2 border border-neutral-700 rounded-lg bg-neutral-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 appearance-none"
                />
              </div>
              {hasDateFilter && (
                <button
                  type="button"
                  onClick={clearDateFilter}
                  className="w-full text-sm text-teal-400 hover:text-teal-300 transition-colors py-1"
                >
                  Clear dates
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
