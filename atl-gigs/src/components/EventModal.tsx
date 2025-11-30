import { Fragment, useState } from "react";
import { Dialog, Transition } from "@headlessui/react";
import { format } from "date-fns";
import { X, MapPin, Clock, Ticket, ExternalLink, Share2, Check, CalendarDays } from "lucide-react";
import { Event } from "../types";

interface EventModalProps {
  event: Event;
  onClose: () => void;
}

export default function EventModal({ event, onClose }: EventModalProps) {
  const [copied, setCopied] = useState(false);
  
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
    room,
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
          <div className="fixed inset-0 bg-neutral-950/90 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-start sm:items-center justify-center p-4 pt-16 sm:pt-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="duration-0"
              enterFrom="opacity-0"
              enterTo="opacity-100"
              leave="duration-0"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-2xl bg-neutral-900 border border-neutral-800 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl">
                {/* Close button */}
                <button
                  type="button"
                  className="absolute right-4 top-4 z-10 rounded-full bg-neutral-800/80 backdrop-blur-sm p-2 text-neutral-400 hover:text-white hover:bg-neutral-700 transition-colors"
                  onClick={onClose}
                >
                  <span className="sr-only">Close</span>
                  <X size={20} />
                </button>

                <div className="sm:flex">
                  {/* Image */}
                  <div className="relative w-full sm:w-72 h-48 sm:h-auto shrink-0">
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
                    <div className="absolute top-4 left-4 flex flex-col items-center justify-center bg-neutral-950/80 backdrop-blur-md border border-white/10 w-14 h-14 rounded-xl">
                      <span className="text-[10px] font-bold text-teal-400 uppercase tracking-wider">
                        {month}
                      </span>
                      <span className="text-xl font-bold text-white leading-none">
                        {day}
                      </span>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-6 flex-1">
                    <Dialog.Title
                      as="h3"
                      className="text-2xl font-bold text-white mb-1"
                    >
                      {artists[0]?.name}
                    </Dialog.Title>

                    {artists.length > 1 && (
                      <p className="text-neutral-400 text-sm mb-4">
                        <span className="text-neutral-500">with</span>{" "}
                        {artists
                          .slice(1)
                          .map((a) => a.name)
                          .join(", ")}
                      </p>
                    )}

                    <div className="space-y-3 mb-6">
                      <div className="flex items-center gap-2 text-neutral-300 text-sm">
                        <MapPin size={14} className="text-teal-500" />
                        <span>{venue}{room && ` · ${room}`}</span>
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

                    <div className="flex flex-wrap gap-3">
                      <button
                        onClick={handleShare}
                        className="flex items-center justify-center w-11 h-11 rounded-xl transition-all bg-neutral-800 hover:bg-neutral-700 text-neutral-400 hover:text-white border border-neutral-700"
                      >
                        {copied ? (
                          <Check size={18} className="text-green-400" />
                        ) : (
                          <Share2 size={18} />
                        )}
                      </button>
                      <a
                        href={ticket_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white shadow-lg shadow-teal-900/20 hover:shadow-teal-900/40 transition-all"
                      >
                        <Ticket size={16} />
                        Tickets
                      </a>
                      {info_url && (
                        <a
                          href={info_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm bg-neutral-800 hover:bg-neutral-700 text-neutral-300 hover:text-white border border-neutral-700 transition-all"
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
