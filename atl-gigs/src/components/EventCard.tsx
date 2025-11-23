import { useState } from "react";
import { format } from "date-fns";
import { MapPin, Clock, Ticket, Share2, Check, CalendarDays } from "lucide-react";
import { Event } from "../types";

interface EventCardProps {
  event: Event;
  onClick: () => void;
}

export default function EventCard({ event, onClick }: EventCardProps) {
  const { venue, date, doors_time, artists, price, image_url, ticket_url, slug } = event;
  const [copied, setCopied] = useState(false);
  
  // Parse date as local time (not UTC) by appending T12:00:00
  const eventDate = new Date(date + "T12:00:00");
  const day = eventDate.getDate();
  const month = format(eventDate, "MMM").toUpperCase();
  const formattedDate = format(eventDate, "EEE, MMM d");
  const mainArtist = artists[0]?.name || "TBA";
  const supportArtists = artists.slice(1).map(a => a.name);

  // Format doors time for display
  const formatTime = (time: string | null) => {
    if (!time) return null;
    const [hours, minutes] = time.split(":");
    const h = parseInt(hours);
    const ampm = h >= 12 ? "PM" : "AM";
    const hour12 = h % 12 || 12;
    return `${hour12.toString().padStart(2, "0")}:${minutes} ${ampm}`;
  };

  const doorsFormatted = formatTime(doors_time);

  const handleShare = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const url = `${window.location.origin}?event=${slug}`;
    
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <div
      className="group relative bg-neutral-900/50 hover:bg-neutral-800/80 border border-neutral-800 hover:border-teal-500/30 rounded-2xl overflow-hidden transition-all duration-300 hover:shadow-[0_0_30px_-10px_rgba(20,184,166,0.15)] flex flex-col sm:flex-row cursor-pointer"
      onClick={onClick}
    >
      {/* Date Badge - Mobile Only */}
      <div className="absolute top-3 left-3 sm:hidden z-10 bg-neutral-950/80 backdrop-blur-md border border-white/10 px-3 py-1 rounded-full text-xs font-bold text-white flex items-center gap-2">
        <span className="text-teal-400">{month} {day}</span>
        <span className="w-1 h-1 bg-neutral-600 rounded-full"></span>
        <span className="text-neutral-300">{venue}</span>
      </div>

      {/* Image Section */}
      <div className="relative w-full sm:w-72 h-48 sm:h-auto shrink-0 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-t from-neutral-900 via-transparent to-transparent sm:hidden z-[1]" />
        {image_url ? (
          <img
            src={image_url}
            alt={mainArtist}
            className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-700 ease-in-out filter brightness-75 group-hover:brightness-100"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-neutral-800 to-neutral-900 flex items-center justify-center">
            <Ticket size={48} className="text-neutral-700" />
          </div>
        )}

        {/* Desktop Date Box overlay on image */}
        <div className="hidden sm:flex absolute top-3 left-3 flex-col items-center justify-center bg-neutral-950/80 backdrop-blur-md border border-white/10 w-14 h-14 rounded-xl shadow-lg z-10">
          <span className="text-[10px] font-bold text-teal-400 uppercase tracking-wider">{month}</span>
          <span className="text-xl font-bold text-white leading-none">{day}</span>
        </div>
      </div>

      {/* Content Section */}
      <div className="flex-1 p-5 sm:p-6 flex flex-col justify-between relative z-[2]">
        {/* Top Info */}
        <div className="mb-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-2xl font-bold text-white group-hover:text-teal-300 transition-colors">
                {mainArtist}
              </h3>
            </div>
          </div>

          {supportArtists.length > 0 && (
            <p className="text-neutral-400 text-sm mt-2 line-clamp-1">
              <span className="text-neutral-500">with</span> {supportArtists.join(", ")}
            </p>
          )}
        </div>

        {/* Details Stack */}
        <div className="space-y-2 text-sm text-neutral-300 mb-6">
          <div className="flex items-center gap-2">
            <MapPin size={14} className="text-teal-500 shrink-0" />
            <span className="truncate">{venue}</span>
          </div>
          <div className="flex items-center gap-2">
            <CalendarDays size={14} className="text-teal-500 shrink-0" />
            <span>{formattedDate}</span>
          </div>
          {doorsFormatted && (
            <div className="flex items-center gap-2">
              <Clock size={14} className="text-teal-500 shrink-0" />
              <span>Doors {doorsFormatted}</span>
            </div>
          )}
          {price && (
            <div className="flex items-center gap-2">
              <Ticket size={14} className="text-teal-500 shrink-0" />
              <span>
                {price === "See website" ? (
                  <span className="text-neutral-500">{price}</span>
                ) : (
                  price
                )}
              </span>
            </div>
          )}
        </div>

        {/* Action Area */}
        <div className="flex items-center justify-center sm:justify-end gap-2 mt-auto">
          {/* Share Button */}
          <button
            onClick={handleShare}
            className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 rounded-lg transition-all duration-300 bg-neutral-800 hover:bg-neutral-700 text-neutral-400 hover:text-white border border-neutral-700"
          >
            {copied ? (
              <Check size={16} className="text-green-400" />
            ) : (
              <Share2 size={16} />
            )}
          </button>

          {/* Get Tickets Button */}
          <a
            href={ticket_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg sm:rounded-xl font-bold text-xs sm:text-sm transition-all duration-300 bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white shadow-lg shadow-teal-900/20 hover:shadow-teal-900/40 hover:-translate-y-0.5"
            onClick={(e) => e.stopPropagation()}
          >
            <Ticket size={14} className="sm:w-4 sm:h-4" />
            Get Tickets
          </a>
        </div>
      </div>
    </div>
  );
}
