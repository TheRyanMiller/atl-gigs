import { Fragment, useState } from "react";
import { Dialog, Transition } from "@headlessui/react";
import { format } from "date-fns";
import { MapPin, Clock, Ticket, ExternalLink, Share2, Check, CalendarDays, Star, Info } from "lucide-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";
import { Event } from "../types";
import { useFavorites } from "../context/FavoritesContext";

interface EventModalProps {
  event: Event;
  onClose: () => void;
}

const DESCRIPTION_PREVIEW_LENGTH = 420;

export default function EventModal({ event, onClose }: EventModalProps) {
  const [copied, setCopied] = useState(false);
  const [descriptionExpanded, setDescriptionExpanded] = useState(false);
  const { isFavorite, toggleFavorite } = useFavorites();

  const {
    venue,
    date,
    doors_time,
    show_time,
    artists,
    price,
    ticket_url,
    info_url,
    image_url,
    slug,
    stage,
    description,
  } = event;
  
  const handleShare = async () => {
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

  // Parse date as local time (not UTC) by appending T12:00:00
  const eventDate = new Date(date + "T12:00:00");
  const formattedDate = format(eventDate, "EEEE, MMMM d, yyyy");
  const day = eventDate.getDate();
  const month = format(eventDate, "MMM").toUpperCase();

  const formatTime = (time: string | null) => {
    if (!time) return null;
    const [hours, minutes] = time.split(":");
    const h = parseInt(hours);
    const ampm = h >= 12 ? "PM" : "AM";
    const hour12 = h % 12 || 12;
    return `${hour12.toString().padStart(2, "0")}:${minutes} ${ampm}`;
  };

  const descriptionText = description?.trim() || "";
  const isLongDescription = descriptionText.length > DESCRIPTION_PREVIEW_LENGTH;
  const visibleDescription =
    isLongDescription && !descriptionExpanded
      ? `${descriptionText.slice(0, DESCRIPTION_PREVIEW_LENGTH).replace(/\s+\S*$/, "")}...`
      : descriptionText;
  const descriptionParagraphs = visibleDescription
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  return (
    <Transition.Root show={true} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="duration-0"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="duration-0"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-neutral-950/95" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-hidden">
          <div className="flex min-h-full items-start justify-center p-4 pt-12 text-center sm:items-center sm:pt-4">
            <Transition.Child
              as={Fragment}
              enter="duration-0"
              enterFrom="opacity-0"
              enterTo="opacity-100"
              leave="duration-0"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <Dialog.Panel className="relative w-full max-h-[calc(100dvh-4rem)] transform overflow-hidden rounded-2xl bg-neutral-900 border-2 border-teal-500/40 text-left shadow-xl sm:my-8 sm:max-h-[calc(100vh-2rem)] sm:max-w-3xl">
                {/* Favorite button - top right */}
                <button
                  type="button"
                  className="absolute right-3 top-3 z-10 rounded-full bg-neutral-800 p-2 text-neutral-400 hover:text-white hover:bg-neutral-700 transition-colors"
                  onClick={() => toggleFavorite(slug)}
                >
                  <span className="sr-only">{isFavorite(slug) ? "Remove from favorites" : "Add to favorites"}</span>
                  <Star
                    size={20}
                    className={isFavorite(slug) ? "fill-yellow-400 text-yellow-400" : ""}
                  />
                </button>

                <div className="flex max-h-[calc(100dvh-4rem)] flex-col sm:h-[36rem] sm:max-h-[calc(100vh-2rem)] sm:flex-row">
                  {/* Image */}
                  <div className="relative w-full h-48 shrink-0 bg-neutral-950 sm:h-full sm:w-72">
                    {image_url ? (
                      <img
                        src={image_url}
                        alt={artists[0]?.name || "Event image"}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-neutral-800 to-neutral-900 flex items-center justify-center">
                        <Ticket size={64} className="text-neutral-700" />
                      </div>
                    )}
                    {/* Date overlay */}
                    <div className="absolute top-4 left-4 flex flex-col items-center justify-center bg-neutral-950 border border-neutral-700 w-14 h-14 rounded-xl">
                      <span className="text-[10px] font-bold text-teal-400 uppercase tracking-wider">
                        {month}
                      </span>
                      <span className="text-xl font-bold text-white leading-none">
                        {day}
                      </span>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-6">
                    <div
                      className="min-h-0 flex-1 overflow-y-auto pr-1 sm:pr-2"
                      data-testid="event-modal-scroll-area"
                    >
                      <Dialog.Title
                        as="h3"
                        className="text-2xl font-bold text-white mb-1 pr-12"
                      >
                        {artists[0]?.name}
                        {artists[0]?.spotify_url && (
                          <a
                            href={artists[0].spotify_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline text-teal-400 hover:text-teal-300 ml-2"
                            aria-label="Open Spotify artist"
                          >
                            <FontAwesomeIcon icon={faSpotify} className="inline-block w-[1.1rem] h-[1.1rem] -translate-y-0.5" />
                          </a>
                        )}
                      </Dialog.Title>

                      {artists.length > 1 && (
                        <p className="text-neutral-400 text-sm mb-4">
                          <span className="text-neutral-500">with</span>{" "}
                          {artists.slice(1).map((artist, index) => (
                            <span key={`${artist.name}-${index}`} className="inline">
                              {index > 0 && ", "}
                              {artist.name}
                              {artist.spotify_url && (
                                <a
                                  href={artist.spotify_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline text-teal-400 hover:text-teal-300 ml-1"
                                  aria-label="Open Spotify artist"
                                >
                                  <FontAwesomeIcon icon={faSpotify} className="inline-block w-[0.66rem] h-[0.66rem] -translate-y-0.5" />
                                </a>
                              )}
                            </span>
                          ))}
                        </p>
                      )}

                      <div className="space-y-3 mb-6">
                        <div className="flex items-center gap-2 text-neutral-300 text-sm">
                          <MapPin size={14} className="text-teal-500" />
                          <span>{venue}{stage && ` (${stage})`}</span>
                        </div>

                        <div className="flex items-center gap-2 text-neutral-300 text-sm">
                          <CalendarDays size={14} className="text-teal-500" />
                          <span>{formattedDate}</span>
                        </div>

                        {doors_time && (
                          <div className="flex items-center gap-2 text-neutral-300 text-sm">
                            <Clock size={14} className="text-teal-500" />
                            <span>
                              Doors {formatTime(doors_time)}
                              {show_time && ` · Show ${formatTime(show_time)}`}
                            </span>
                          </div>
                        )}

                        {price && (
                          <div className="flex items-center gap-2 text-neutral-300 text-sm">
                            <Ticket size={14} className="text-teal-500" />
                            <span>{price}</span>
                          </div>
                        )}
                      </div>

                      {descriptionText && (
                        <div className="mb-6 border-t border-neutral-800 pt-5 sm:mb-4">
                          <div className="flex items-center gap-2 text-sm font-semibold text-neutral-100 mb-2">
                            <Info size={14} className="text-teal-500" />
                            <span>About</span>
                          </div>
                          <div className="space-y-3 text-sm leading-6 text-neutral-300">
                            {descriptionParagraphs.map((paragraph, index) => (
                              <p key={index}>{paragraph}</p>
                            ))}
                          </div>
                          {isLongDescription && (
                            <button
                              type="button"
                              onClick={() => setDescriptionExpanded((expanded) => !expanded)}
                              className="mt-3 text-sm font-medium text-teal-400 hover:text-teal-300 transition-colors"
                            >
                              {descriptionExpanded ? "Show less" : "Show more"}
                            </button>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="mt-4 flex shrink-0 flex-wrap gap-3 border-t border-neutral-800 pt-4">
                      <button
                        onClick={handleShare}
                        className="flex items-center justify-center w-12 h-12 rounded-xl transition-colors bg-neutral-800 hover:bg-neutral-700 text-neutral-400 hover:text-white border border-neutral-700"
                      >
                        {copied ? (
                          <Check size={18} className="text-green-400" />
                        ) : (
                          <Share2 size={18} className="text-teal-400" />
                        )}
                      </button>
                      <a
                        href={ticket_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white transition-colors"
                      >
                        <Ticket size={16} />
                        Tickets
                      </a>
                      {info_url && (
                        <a
                          href={info_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm bg-neutral-800 hover:bg-neutral-700 text-neutral-300 hover:text-white border border-neutral-700 transition-colors"
                        >
                          <ExternalLink size={16} />
                          Info
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}
