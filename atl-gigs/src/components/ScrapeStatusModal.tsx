import { format } from "date-fns";
import { ScrapeStatus } from "../types";

interface ScrapeStatusModalProps {
  status: ScrapeStatus;
  onClose: () => void;
}

export default function ScrapeStatusModal({
  status,
  onClose,
}: ScrapeStatusModalProps) {
  const formatDate = (isoString: string | undefined) => {
    if (!isoString) return "Never";
    try {
      return format(new Date(isoString), "MMM d, yyyy 'at' h:mm a");
    } catch {
      return isoString;
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-zinc-800 rounded-lg shadow-xl max-w-lg w-full max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-gray-200 dark:border-zinc-700 flex items-center justify-center relative">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-zinc-100">
            Status
          </h2>
          <button
            onClick={onClose}
            className="absolute right-4 text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-200"
            aria-label="Close"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="p-4 overflow-y-auto max-h-[calc(80vh-60px)]">
          {/* Overall Status */}
          <div className="mb-4 p-3 rounded-lg bg-gray-50 dark:bg-zinc-700/50">
            <div className="flex items-center gap-2 mb-2">
              <span
                className={`w-3 h-3 rounded-full ${
                  status.all_success
                    ? "bg-green-500"
                    : status.any_success
                    ? "bg-yellow-500"
                    : "bg-red-500"
                }`}
              />
              <span className="font-medium text-gray-900 dark:text-zinc-100">
                {status.all_success
                  ? "All Systems Operational"
                  : status.any_success
                  ? "Partial Outage"
                  : "Major Outage"}
              </span>
            </div>
            <div className="text-sm text-gray-600 dark:text-zinc-300">
              <p>Last run: {formatDate(status.last_run)}</p>
              <p>Total events: {status.total_events}</p>
            </div>
          </div>

          {/* Per-Venue Status */}
          <h3 className="text-sm font-medium text-gray-700 dark:text-zinc-300 mb-2">
            Venue Status
          </h3>
          <div className="space-y-2">
            {Object.entries(status.venues).map(([venueName, venueStatus]) => (
              <div
                key={venueName}
                className={`p-3 rounded-lg border ${
                  venueStatus.success
                    ? "border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20"
                    : "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        venueStatus.success ? "bg-green-500" : "bg-red-500"
                      }`}
                    />
                    <span className="font-medium text-gray-900 dark:text-zinc-100">
                      {venueName}
                    </span>
                  </div>
                  {venueStatus.success && (
                    <span className="text-sm text-gray-600 dark:text-zinc-400">
                      {venueStatus.event_count} events
                    </span>
                  )}
                </div>

                <div className="text-xs text-gray-500 dark:text-zinc-400 space-y-0.5">
                  {venueStatus.success ? (
                    <p>Last success: {formatDate(venueStatus.last_success)}</p>
                  ) : (
                    <>
                      <p className="text-red-600 dark:text-red-400">
                        Error: {venueStatus.error}
                      </p>
                      {venueStatus.last_success && (
                        <p>
                          Last success: {formatDate(venueStatus.last_success)} (
                          {venueStatus.last_success_count} events)
                        </p>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
