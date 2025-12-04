import { BrowserRouter as Router, Routes, Route, useSearchParams } from "react-router-dom";
import { useState, useEffect, useCallback } from "react";
import Home from "./pages/Home";
import Favorites from "./pages/Favorites";
import Header from "./components/Header";
import EventModal from "./components/EventModal";
import ScrapeStatusModal from "./components/ScrapeStatusModal";
import { FavoritesProvider } from "./context/FavoritesContext";
import { Event, ScrapeStatus } from "./types";

function AppContent() {
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
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
    // R2 public URL for event data (used in both dev and prod)
    const R2_BASE_URL = "https://pub-756023fa49674586a44105ba7bf52137.r2.dev";
    const EVENTS_URL = `${R2_BASE_URL}/events.json?v=${Date.now()}`;

    fetch(EVENTS_URL)
      .then((response) => {
        if (!response.ok) {
          // No events file yet - treat as empty
          return [];
        }
        return response.json();
      })
      .then((data) => {
        const events = Array.isArray(data) ? data : [];
        setEvents(events);
        setLoading(false);

        // Check for event slug in URL and open modal
        const eventSlug = searchParams.get("event");
        if (eventSlug) {
          const event = events.find((e: Event) => e.slug === eventSlug);
          if (event) {
            setSelectedEvent(event);
          }
        }
      })
      .catch((error) => {
        console.error("Error fetching events:", error);
        // Treat fetch errors as empty events, not a blocking error
        setEvents([]);
        setLoading(false);
      });

    const STATUS_URL = `${R2_BASE_URL}/scrape-status.json`;

    fetch(STATUS_URL)
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
      <main>
        <Routes>
          <Route
            path="/"
            element={<Home events={events} loading={loading} onEventClick={handleEventSelect} />}
          />
          <Route
            path="/favorites"
            element={<Favorites events={events} loading={loading} onEventClick={handleEventSelect} />}
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
    <FavoritesProvider>
      <Router>
        <AppContent />
      </Router>
    </FavoritesProvider>
  );
}

export default App;
