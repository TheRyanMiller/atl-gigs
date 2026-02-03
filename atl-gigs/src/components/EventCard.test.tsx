import { render, screen } from "@testing-library/react";
import EventCard from "./EventCard";
import { FavoritesProvider } from "../context/FavoritesContext";
import { Event } from "../types";

const baseEvent: Event = {
  slug: "2026-02-10-center-stage-artist",
  venue: "Center Stage",
  date: "2026-02-10",
  doors_time: "19:00",
  show_time: "20:00",
  artists: [
    { name: "Scott Ivey", spotify_url: "https://open.spotify.com/artist/AAA" },
    { name: "The Filthy Frets", spotify_url: "https://open.spotify.com/artist/BBB" },
  ],
  price: "$20",
  ticket_url: "https://example.com/tickets",
  category: "concerts",
};

const renderWithProviders = (event: Event) =>
  render(
    <FavoritesProvider>
      <EventCard event={event} onClick={() => undefined} />
    </FavoritesProvider>
  );


test("shows Spotify icons when spotify_url is present", () => {
  renderWithProviders(baseEvent);
  const icons = screen.getAllByLabelText("Open Spotify artist");
  expect(icons.length).toBe(2);
});

test("hides Spotify icons when spotify_url is missing", () => {
  const event = { ...baseEvent, artists: [{ name: "No Link" }] };
  renderWithProviders(event);
  expect(screen.queryByLabelText("Open Spotify artist")).toBeNull();
});
