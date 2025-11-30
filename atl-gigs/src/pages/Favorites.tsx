import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Star, Loader2 } from "lucide-react";
import { Event } from "../types";
import EventCard from "../components/EventCard";
import { useFavorites } from "../context/FavoritesContext";

interface FavoritesProps {
  events: Event[];
  loading: boolean;
  onEventClick: (event: Event) => void;
}

export default function Favorites({ events, loading, onEventClick }: FavoritesProps) {
  const { favorites, favoriteCount, clearFavorites } = useFavorites();

  // Get today's date in YYYY-MM-DD format for comparison (local timezone)
  const getTodayString = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  // Filter events to only show favorited ones that haven't passed
  const favoriteEvents = useMemo(() => {
    const today = getTodayString();
    return events
      .filter((event) => favorites.has(event.slug) && event.date >= today)
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [events, favorites]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col items-center gap-4">
        <div className="flex items-center gap-3">
          <Star size={24} className="text-yellow-400 fill-yellow-400" />
          <h1 className="text-2xl font-bold text-white">
            Your Favorites
            {favoriteCount > 0 && (
              <span className="text-neutral-500 font-normal ml-2">
                ({favoriteCount})
              </span>
            )}
          </h1>
        </div>

        {favoriteCount > 0 && (
          <button
            onClick={clearFavorites}
            className="text-xs text-neutral-500 hover:text-red-400 transition-colors"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Events List */}
      <div className="space-y-4">
        {favoriteEvents.map((event, index) => (
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

        {!loading && favoriteEvents.length === 0 && (
          <div className="text-center py-20 bg-neutral-900/30 rounded-3xl border border-neutral-800 border-dashed">
            <Star size={48} className="mx-auto text-neutral-700 mb-4" />
            <h3 className="text-xl font-bold text-white">No favorites yet</h3>
            <p className="text-neutral-500 mt-2 max-w-sm mx-auto">
              Star events you're interested in to save them here for quick access.
            </p>
            <Link
              to="/"
              className="inline-flex items-center gap-2 mt-6 px-5 py-2.5 rounded-xl font-bold text-sm bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white shadow-lg shadow-teal-900/20 transition-all"
            >
              Browse Events
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
