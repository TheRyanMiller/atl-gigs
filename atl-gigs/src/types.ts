export interface Artist {
  name: string;
  genre?: string;
}

export type EventCategory = "concerts" | "comedy" | "broadway" | "sports" | "misc";

export const CATEGORY_LABELS: Record<EventCategory, string> = {
  concerts: "Concerts",
  comedy: "Comedy",
  broadway: "Broadway",
  sports: "Sports",
  misc: "Other",
};

export const ALL_CATEGORIES: EventCategory[] = ["concerts", "comedy", "broadway", "sports", "misc"];

export interface Event {
  slug: string;
  venue: string;
  date: string;
  doors_time: string | null;
  show_time: string | null;
  artists: Artist[];
  price?: string;
  ticket_url: string;
  info_url?: string;
  image_url?: string;
  category: EventCategory;
  stage?: string;  // For venues with multiple stages (e.g., The Masquerade, Center Stage)
  first_seen?: string;  // ISO timestamp when event was first discovered
  is_new?: boolean;  // Pre-calculated by scraper based on first_seen
  last_seen?: string;  // ISO timestamp when scraper last found this event (for stale detection)
}

export interface VenueStatus {
  last_run: string;
  success: boolean;
  event_count: number;
  error: string | null;
  error_trace?: string;
  last_success?: string;
  last_success_count?: number;
}

export interface ScrapeStatus {
  last_run: string;
  all_success: boolean;
  any_success: boolean;
  total_events: number;
  venues: Record<string, VenueStatus>;
}
