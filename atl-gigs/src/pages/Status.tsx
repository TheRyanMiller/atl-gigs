import { format } from "date-fns";

interface StatusProps {
  lastScrape: string;
  eventCount: number;
}

export default function Status({ lastScrape, eventCount }: StatusProps) {
  const formattedDate = lastScrape
    ? format(new Date(lastScrape), "PPpp")
    : "Never";
  const isHealthy =
    lastScrape &&
    Date.now() - new Date(lastScrape).getTime() < 24 * 60 * 60 * 1000; // Within 24 hours

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">API Status</h1>

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center mb-6">
          <div
            className={`w-3 h-3 rounded-full mr-2 ${
              isHealthy ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="text-lg font-medium">
            {isHealthy ? "API is healthy" : "API needs attention"}
          </span>
        </div>

        <div className="space-y-4">
          <div>
            <h2 className="text-sm font-medium text-gray-500">Last Scrape</h2>
            <p className="mt-1 text-lg">{formattedDate}</p>
          </div>

          <div>
            <h2 className="text-sm font-medium text-gray-500">Total Events</h2>
            <p className="mt-1 text-lg">{eventCount}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
