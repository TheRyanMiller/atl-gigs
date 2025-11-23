import { format } from "date-fns";
import { Event } from "../types";

interface EventCardProps {
  event: Event;
  onClick: () => void;
}

export default function EventCard({ event, onClick }: EventCardProps) {
  const { venue, date, doors_time, show_time, artists, price, image_url } =
    event;
  const formattedDate = format(new Date(date), "EEEE, MMMM d, yyyy");
  const mainArtist = artists[0]?.name;

  // Price is already normalized by scraper - null means unavailable
  const showPrice = !!price;

  return (
    <div
      className="bg-white dark:bg-zinc-800 border border-gray-100 dark:border-zinc-700/50 rounded-xl shadow-[0_1px_3px_rgba(0,0,0,0.12),0_1px_2px_rgba(0,0,0,0.08)] dark:shadow-[0_1px_3px_rgba(0,0,0,0.4),0_1px_2px_rgba(0,0,0,0.3)] hover:shadow-[0_2px_6px_rgba(0,0,0,0.15),0_1px_3px_rgba(0,0,0,0.1)] dark:hover:shadow-[0_2px_6px_rgba(0,0,0,0.5),0_1px_3px_rgba(0,0,0,0.4)] hover:-translate-y-0.5 transition-all duration-200 cursor-pointer mb-6 h-56 overflow-hidden flex"
      onClick={onClick}
      style={{ minHeight: 224, maxHeight: 224 }}
    >
      {image_url && (
        <div className="w-1/3 p-3 flex items-center justify-center h-full">
          <img
            src={image_url}
            alt={mainArtist || "Event image"}
            className="w-full h-full object-cover rounded-lg shadow-sm"
            style={{ maxHeight: 176, maxWidth: "100%" }}
          />
        </div>
      )}
      <div
        className={`p-4 flex flex-col justify-between ${
          image_url ? "w-2/3" : "w-full"
        } h-full`}
      >
        <div>
          <h2 className="text-2xl font-bold font-montserrat mb-2 text-gray-900 dark:text-zinc-100">
            {mainArtist}
          </h2>

          {artists.length > 1 && (
            <p className="text-sm text-gray-600 dark:text-zinc-300 mb-2">
              with{" "}
              {artists
                .slice(1)
                .map((a) => a.name)
                .join(", ")}
            </p>
          )}

          <div className="text-sm text-gray-600 dark:text-zinc-300 mb-2">
            <p>{formattedDate}</p>
            <p>{venue}</p>
            {doors_time && show_time && (
              <p>
                Doors: {doors_time} | Show: {show_time}
              </p>
            )}
          </div>

          {showPrice && (
            <p className="text-sm font-medium text-gray-900 dark:text-zinc-100">
              {price}
            </p>
          )}
        </div>
        <a
          href={event.ticket_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 w-fit inline-flex px-4 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 active:bg-purple-800 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 text-sm font-medium shadow-sm hover:shadow"
          onClick={(e) => e.stopPropagation()}
        >
          Buy Tickets
        </a>
      </div>
    </div>
  );
}
