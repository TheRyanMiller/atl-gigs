import { BrowserRouter as Router, Routes, Route, useSearchParams } from "react-router-dom";
import { useState, useEffect, useCallback } from "react";
import Home from "./pages/Home";
import Header from "./components/Header";
import EventModal from "./components/EventModal";
import ScrapeStatusModal from "./components/ScrapeStatusModal";
import { Event, ScrapeStatus } from "./types";

function AppContent() {
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scrapeStatus, setScrapeStatus] = useState<ScrapeStatus | null>(null);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  // Handle event selection with URL update
  const handleEventSelect = useCallback((event: Event | null) => {
    setSelectedEvent(event);
    if (event) {
      setSearchParams({ event: event.slug });
    } else {
      setSearchParams({});
    }
  }, [setSearchParams]);

  // Handle modal close
  const handleModalClose = useCallback(() => {
    setSelectedEvent(null);
    setSearchParams({});
  }, [setSearchParams]);

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
        setError(null);

        // Check for event slug in URL and open modal
        const eventSlug = searchParams.get("event");
        if (eventSlug) {
          const event = data.find((e: Event) => e.slug === eventSlug);
          if (event) {
            setSelectedEvent(event);
          }
        }
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
    <div className="bg-neutral-950 text-neutral-200 font-sans selection:bg-teal-500/30 selection:text-teal-200">
      <Header
        status={scrapeStatus}
        onStatusClick={() => setShowStatusModal(true)}
      />

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-4 sm:py-12 pb-8 sm:pb-12">
        {error && (
          <div
            className="bg-red-900/20 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl mb-6"
            role="alert"
          >
            <strong className="font-bold">Error: </strong>
            <span>{error}</span>
          </div>
        )}

        <Routes>
          <Route
            path="/"
            element={<Home events={events} onEventClick={handleEventSelect} />}
          />
        </Routes>
      </main>

      {selectedEvent && (
        <EventModal
          event={selectedEvent}
          onClose={handleModalClose}
        />
      )}

      {showStatusModal && scrapeStatus && (
        <ScrapeStatusModal
          status={scrapeStatus}
          onClose={() => setShowStatusModal(false)}
        />
      )}
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
