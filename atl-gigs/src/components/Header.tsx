import { Music, Github, Star } from "lucide-react";
import { Link } from "react-router-dom";
import { ScrapeStatus } from "../types";
import { useFavorites } from "../context/FavoritesContext";

interface HeaderProps {
  status: ScrapeStatus | null;
  onStatusClick: () => void;
}

export default function Header({ status, onStatusClick }: HeaderProps) {
  const isHealthy = status?.all_success ?? true;
  const { favoriteCount } = useFavorites();

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-neutral-950">
      <div className="max-w-5xl mx-auto px-4 h-14 sm:h-20 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-teal-600 to-cyan-600 rounded-lg sm:rounded-xl flex items-center justify-center">
            <Music size={16} className="sm:w-5 sm:h-5 text-white" />
          </div>
          <span className="text-lg sm:text-xl font-bold text-white tracking-tight leading-none group-hover:text-teal-300 transition-colors">
            ATL<span className="text-teal-500">Gigs</span>
          </span>
        </Link>

        {/* Nav */}
        <nav className="hidden md:flex flex-col items-end gap-1 text-sm font-medium text-neutral-400">
          {/* Favorites Link */}
          <Link
            to="/favorites"
            className="flex items-center gap-1.5 hover:text-white transition-colors"
          >
            <span className="relative">
              <Star size={14} className={favoriteCount > 0 ? "fill-yellow-400 text-yellow-400" : ""} />
              {favoriteCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 min-w-[14px] h-[14px] flex items-center justify-center bg-yellow-500 text-[9px] font-bold text-neutral-900 rounded-full px-0.5">
                  {favoriteCount > 99 ? "99+" : favoriteCount}
                </span>
              )}
            </span>
            <span className="text-xs">Favorites</span>
          </Link>

          {/* Status Indicator */}
          <button
            onClick={onStatusClick}
            className="flex items-center gap-1.5 hover:text-white transition-colors"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy ? "bg-green-500 animate-pulse" : "bg-red-500"
              }`}
            />
            <span className="text-xs">
              {status ? `${status.total_events} events` : "Loading..."}
            </span>
          </button>

          {/* GitHub */}
          <a
            href="https://github.com/TheRyanMiller/atl-gigs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-[11px] text-neutral-500 hover:text-white transition-colors"
          >
            <Github size={12} />
            <span>Source</span>
          </a>
        </nav>

        {/* Mobile Icons */}
        <div className="flex md:hidden items-center gap-3">
          {/* Favorites Link */}
          <Link
            to="/favorites"
            className="relative text-neutral-400 hover:text-white"
          >
            <Star size={18} className={favoriteCount > 0 ? "fill-yellow-400 text-yellow-400" : ""} />
            {favoriteCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 min-w-[14px] h-[14px] flex items-center justify-center bg-yellow-500 text-[9px] font-bold text-neutral-900 rounded-full px-0.5">
                {favoriteCount > 99 ? "99+" : favoriteCount}
              </span>
            )}
          </Link>
          <button
            onClick={onStatusClick}
            className="flex items-center gap-1.5 text-neutral-400 hover:text-white"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy ? "bg-green-500 animate-pulse" : "bg-red-500"
              }`}
            />
          </button>
          <a
            href="https://github.com/TheRyanMiller/atl-gigs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-neutral-400 hover:text-white"
          >
            <Github size={18} />
          </a>
        </div>
      </div>
    </header>
  );
}
