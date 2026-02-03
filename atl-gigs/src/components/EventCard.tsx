import { useState, memo } from "react";
import { format } from "date-fns";
import { MapPin, Clock, Ticket, Share2, Check, CalendarDays, Star } from "lucide-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";
import { faGuitar, faFaceLaughSquint, faMasksTheater, faFootball, faStar } from "@fortawesome/free-solid-svg-icons";
import { Event, CATEGORY_LABELS } from "../types";
import { useFavorites } from "../context/FavoritesContext";

const categoryIcons = {
  concerts: faGuitar,
  comedy: faFaceLaughSquint,
  broadway: faMasksTheater,
  sports: faFootball,
  misc: faStar,
};

interface EventCardProps {
  event: Event;
  onClick: () => void;
  mobileHeight?: number;
}

function EventCard({ event, onClick, mobileHeight }: EventCardProps) {
  const { venue, date, doors_time, artists, price, image_url, ticket_url, slug, category, is_new, stage } = event;
  const [copied, setCopied] = useState(false);
  const { isFavorite, toggleFavorite } = useFavorites();
  const favorited = isFavorite(slug);

  const handleFavorite = (e: React.MouseEvent) => {
    e.stopPropagation();
    toggleFavorite(slug);
  };

  // Parse date as local time (not UTC) by appending T12:00:00
  const eventDate = new Date(date + "T12:00:00");
  const day = eventDate.getDate();
  const month = format(eventDate, "MMM").toUpperCase();
  const formattedDate = format(eventDate, "EEE, MMM d");
  const mainArtist = artists[0]?.name || "TBA";
  const supportArtists = artists.slice(1);

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
    // Use /e/slug format for sharing - this route serves OG tags to crawlers
    const url = `${window.location.origin}/e/${slug}`;

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
      className="group relative bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 hover:border-teal-500/30 rounded-2xl overflow-hidden transition-colors duration-200 flex flex-col sm:flex-row sm:items-stretch cursor-pointer sm:h-[195px]"
      style={mobileHeight ? { height: mobileHeight } : undefined}
      onClick={onClick}
    >
      {/* Image Section */}
      <div className="relative w-full h-[147px] sm:h-auto sm:min-h-[160px] sm:w-52 sm:self-stretch shrink-0 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-t from-neutral-900 via-transparent to-transparent sm:hidden z-[1]" />
        {image_url ? (
          <img
            src={image_url}
            alt={mainArtist}
            className="absolute inset-0 w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-neutral-800 to-neutral-900 flex items-center justify-center">
            <Ticket size={48} className="text-neutral-700" />
          </div>
        )}

        {/* Date Box overlay on image */}
        <div className="flex absolute top-1.5 left-2 sm:top-1.5 sm:left-1.5 flex-col items-center justify-center bg-neutral-950 border border-neutral-700 w-11 h-11 rounded-xl z-10">
          <span className="text-[9px] font-bold text-teal-400 uppercase tracking-wider">{month}</span>
          <span className="text-base font-bold text-white leading-none">{day}</span>
        </div>

        {/* New Badge overlay on image (bottom right) */}
        {is_new && (
          <div className="absolute bottom-1.5 right-1 sm:bottom-1.5 sm:right-1.5 bg-teal-400 text-neutral-900 text-[9px] font-bold uppercase tracking-tight px-1.5 py-0.5 rounded z-10 shadow-md shadow-black/50 border border-black/30">
            Just Added!
          </div>
        )}
      </div>

      {/* Category Badge - Top right of card (desktop only) */}
      <div className="hidden sm:flex absolute top-3 right-5 z-10 items-center gap-1 bg-neutral-800/90 border border-neutral-700 px-1.5 py-0.5 rounded">
        <FontAwesomeIcon icon={categoryIcons[category]} className="w-2.5 h-2.5 text-neutral-400" />
        <span className="text-[10px] font-medium text-neutral-400">{CATEGORY_LABELS[category]}</span>
      </div>

      {/* Content + Actions */}
      <div className="flex flex-1 flex-col sm:flex-row sm:items-start relative z-[2] p-4 sm:px-5 sm:pt-5 pb-3 sm:pb-3 gap-4 sm:gap-6">
        {/* Category Badge - Mobile only, top right of content area */}
        <div className="flex sm:hidden absolute top-3 right-3 z-10 items-center gap-1 bg-neutral-800/90 border border-neutral-700 px-1.5 py-0.5 rounded">
          <FontAwesomeIcon icon={categoryIcons[category]} className="w-2.5 h-2.5 text-neutral-400" />
          <span className="text-[10px] font-medium text-neutral-400">{CATEGORY_LABELS[category]}</span>
        </div>

        {/* Text block */}
        <div className="flex-1 sm:w-[70%]">
          <div className="mb-2.5">
            <h3 className="text-lg sm:text-xl font-bold text-white group-hover:text-teal-300 transition-colors leading-snug pr-20 sm:pr-0 line-clamp-2">
              <span className="inline-flex items-center gap-1">
                {mainArtist}
                {artists[0]?.spotify_url && (
                  <a
                    href={artists[0].spotify_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-teal-400 hover:text-teal-300"
                    onClick={(e) => e.stopPropagation()}
                    aria-label="Open Spotify artist"
                  >
                    <FontAwesomeIcon icon={faSpotify} className="w-[1.3rem] h-[1.3rem] ml-2 relative -top-1" />
                  </a>
                )}
              </span>
            </h3>

            {supportArtists.length > 0 && (
              <p className="text-neutral-400 text-sm mt-2 line-clamp-1">
                <span className="text-neutral-500">with</span>{" "}
                {supportArtists.map((artist, index) => (
                  <span key={`${artist.name}-${index}`} className="inline-flex items-center gap-1">
                    {index > 0 && ", "}
                    {artist.name}
                    {artist.spotify_url && (
                      <a
                        href={artist.spotify_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-teal-400 hover:text-teal-300"
                        onClick={(e) => e.stopPropagation()}
                        aria-label="Open Spotify artist"
                      >
                        <FontAwesomeIcon icon={faSpotify} className="w-[1.3rem] h-[1.3rem] ml-2 relative -top-1" />
                      </a>
                    )}
                  </span>
                ))}
              </p>
            )}
          </div>

          <div className="space-y-1.5 text-sm text-neutral-300">
            <div className="flex items-center gap-2">
              <MapPin size={14} className="text-teal-500 shrink-0" />
              <span className="truncate">{venue}{stage && ` (${stage})`}</span>
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
                    <span className="text-neutral-500">See website for prices</span>
                  ) : (
                    price
                  )}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Action Area */}
        <div className="flex items-center justify-center sm:justify-end gap-2 sm:w-[30%] sm:ml-auto sm:self-stretch sm:flex-row sm:items-center sm:gap-3 sm:mt-auto sm:mb-1">
          {/* Share Button */}
          <button
            onClick={handleShare}
            className="flex items-center justify-center w-10 h-10 shrink-0 rounded-lg transition-colors bg-neutral-800 hover:bg-neutral-700 border border-neutral-700"
          >
            {copied ? (
              <Check size={14} className="text-green-400" />
            ) : (
              <Share2 size={16} className="text-teal-400" />
            )}
          </button>

          {/* Favorite Button */}
          <button
            onClick={handleFavorite}
            className="flex items-center justify-center w-10 h-10 shrink-0 rounded-lg transition-colors bg-neutral-800 hover:bg-neutral-700 border border-neutral-700"
          >
            <Star
              size={16}
              className={favorited ? "fill-yellow-400 text-yellow-400" : "text-teal-400"}
            />
          </button>

          {/* Get Tickets Button */}
          <a
            href={ticket_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-4 py-2 shrink-0 rounded-lg font-bold text-sm transition-colors bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white whitespace-nowrap"
            onClick={(e) => e.stopPropagation()}
          >
            <Ticket size={14} />
            Get Tickets
          </a>

        </div>
      </div>
    </div>
  );
}

export default memo(EventCard);
