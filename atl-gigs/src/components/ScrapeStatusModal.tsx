import { format } from "date-fns";
import { X } from "lucide-react";
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
      className="fixed inset-0 bg-neutral-950/90 backdrop-blur-sm flex items-start sm:items-center justify-center z-50 p-4 pt-16 sm:pt-4"
      onClick={onClose}
    >
      <div
        className="bg-neutral-900 border border-neutral-800 rounded-2xl shadow-xl max-w-lg w-full max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-neutral-800 flex items-center justify-center relative">
          <h2 className="text-lg font-semibold text-white">Status</h2>
          <button
            onClick={onClose}
            className="absolute right-4 text-neutral-400 hover:text-white transition-colors"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-4 overflow-y-auto max-h-[calc(80vh-60px)]">
          {/* Overall Status */}
          <div className="mb-4 p-4 rounded-xl bg-neutral-800/50 border border-neutral-700/50">
            <div className="flex items-center gap-2 mb-2">
              <span
                className={`w-3 h-3 rounded-full ${
                  status.all_success
                    ? "bg-green-500"
                    : status.any_success
                    ? "bg-amber-500"
                    : "bg-red-500"
                }`}
              />
              <span className="font-medium text-white">
                {status.all_success
                  ? "All Systems Operational"
                  : status.any_success
                  ? "Partial Outage"
                  : "Major Outage"}
              </span>
            </div>
            <div className="text-sm text-neutral-400 space-y-1">
              <p>Last run: {formatDate(status.last_run)}</p>
              <p>Total events: {status.total_events}</p>
            </div>
          </div>

          {/* Per-Venue Status */}
          <h3 className="text-sm font-medium text-neutral-400 mb-3">
            Venue Status
          </h3>
          <div className="space-y-2">
            {Object.entries(status.venues).map(([venueName, venueStatus]) => (
              <div
                key={venueName}
                className={`p-3 rounded-xl border ${
                  venueStatus.success
                    ? "border-green-500/20 bg-green-500/5"
                    : "border-red-500/20 bg-red-500/5"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        venueStatus.success ? "bg-green-500" : "bg-red-500"
                      }`}
                    />
                    <span className="font-medium text-white">{venueName}</span>
                  </div>
                  {venueStatus.success && (
                    <span className="text-sm text-neutral-500">
                      {venueStatus.event_count} events
                    </span>
                  )}
                </div>

                <div className="text-xs text-neutral-500 space-y-0.5">
                  {venueStatus.success ? (
                    <p>Last success: {formatDate(venueStatus.last_success)}</p>
                  ) : (
                    <>
                      <p className="text-red-400">Error: {venueStatus.error}</p>
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
