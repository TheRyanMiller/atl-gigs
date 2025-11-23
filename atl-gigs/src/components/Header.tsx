import { Music, Github } from "lucide-react";
import { ScrapeStatus } from "../types";

interface HeaderProps {
  status: ScrapeStatus | null;
  onStatusClick: () => void;
}

export default function Header({ status, onStatusClick }: HeaderProps) {
  const isHealthy = status?.all_success ?? true;

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-neutral-950/80 backdrop-blur-xl">
      <div className="max-w-5xl mx-auto px-4 h-20 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2 group cursor-pointer">
          <div className="w-10 h-10 bg-gradient-to-br from-teal-600 to-cyan-600 rounded-xl flex items-center justify-center shadow-lg shadow-teal-900/20 group-hover:scale-105 transition-transform">
            <Music size={20} className="text-white" />
          </div>
          <span className="text-xl font-bold text-white tracking-tight leading-none group-hover:text-teal-300 transition-colors">
            ATL<span className="text-teal-500">Gigs</span>
          </span>
        </div>

        {/* Nav */}
        <nav className="hidden md:flex flex-col items-end gap-1 text-sm font-medium text-neutral-400">
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
        <div className="flex md:hidden items-center gap-4">
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
            className="p-2 text-neutral-400 hover:text-white"
          >
            <Github size={20} />
          </a>
        </div>
      </div>
    </header>
  );
}
