import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { useState, useEffect } from "react";
import Home from "./pages/Home";
import Status from "./pages/Status";
import EventModal from "./components/EventModal";
import Footer from "./components/Footer";
import ScrapeStatusModal from "./components/ScrapeStatusModal";
import { Event, ScrapeStatus } from "./types";

function App() {
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [lastScrape, setLastScrape] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [scrapeStatus, setScrapeStatus] = useState<ScrapeStatus | null>(null);
  const [showStatusModal, setShowStatusModal] = useState(false);

  useEffect(() => {
    // Fetch events
    fetch("/events.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (!Array.isArray(data)) {
          throw new Error("Data is not an array!");
        }
        setEvents(data);
        setLastScrape(new Date().toISOString());
        setError(null);
      })
      .catch((error) => {
        console.error("Error fetching events:", error);
        setError(error.message);
      });

    // Fetch scrape status
    fetch("/scrape-status.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        setScrapeStatus(data);
      })
      .catch((error) => {
        console.error("Error fetching scrape status:", error);
      });
  }, []);

  return (
    <Router>
      <div className="min-h-screen w-full bg-gray-50 text-gray-900 dark:bg-zinc-900 dark:text-zinc-100 pb-12">
        {error && (
          <div
            className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative"
            role="alert"
          >
            <strong className="font-bold">Error!</strong>
            <span className="block sm:inline"> {error}</span>
          </div>
        )}

        <Routes>
          <Route
            path="/"
            element={<Home events={events} onEventClick={setSelectedEvent} />}
          />
          <Route
            path="/status"
            element={
              <Status lastScrape={lastScrape} eventCount={events.length} />
            }
          />
        </Routes>

        {selectedEvent && (
          <EventModal
            event={selectedEvent}
            onClose={() => setSelectedEvent(null)}
          />
        )}

        {showStatusModal && scrapeStatus && (
          <ScrapeStatusModal
            status={scrapeStatus}
            onClose={() => setShowStatusModal(false)}
          />
        )}

        <Footer
          status={scrapeStatus}
          onStatusClick={() => setShowStatusModal(true)}
        />
      </div>
    </Router>
  );
}

export default App;
