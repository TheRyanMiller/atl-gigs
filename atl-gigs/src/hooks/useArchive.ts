import { useState, useEffect, useCallback } from "react";
import { Event, ArchiveIndex } from "../types";

interface UseArchiveResult {
  archiveIndex: ArchiveIndex | null;
  archiveEvents: Event[];
  loadMonth: (month: string) => Promise<void>;
  loadAllMonths: () => Promise<void>;
  loadMonthsForRange: (startDate: string, endDate: string | null) => Promise<void>;
  loading: boolean;
  loadedMonths: Set<string>;
}

export function useArchive(): UseArchiveResult {
  const [archiveIndex, setArchiveIndex] = useState<ArchiveIndex | null>(null);
  const [archiveEvents, setArchiveEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadedMonths, setLoadedMonths] = useState<Set<string>>(new Set());

  // Load archive index on mount
  useEffect(() => {
    fetch("/events/archive/index.json")
      .then((res) => {
        if (!res.ok) throw new Error("No archive index");
        return res.json();
      })
      .then(setArchiveIndex)
      .catch(() => setArchiveIndex(null));
  }, []);

  const loadMonth = useCallback(async (month: string) => {
    if (loadedMonths.has(month)) return;

    setLoading(true);
    try {
      const res = await fetch(`/events/archive/archive-${month}.json`);
      if (!res.ok) throw new Error(`Failed to load ${month}`);

      const events: Event[] = await res.json();

      setArchiveEvents((prev) => {
        // Merge and deduplicate by slug
        const slugs = new Set(prev.map((e) => e.slug));
        const newEvents = events.filter((e) => !slugs.has(e.slug));
        return [...prev, ...newEvents];
      });

      setLoadedMonths((prev) => new Set([...prev, month]));
    } catch (err) {
      console.error(`Failed to load archive month ${month}:`, err);
    } finally {
      setLoading(false);
    }
  }, [loadedMonths]);

  const loadAllMonths = useCallback(async () => {
    if (!archiveIndex) return;

    setLoading(true);
    try {
      const unloaded = archiveIndex.months
        .map((m) => m.month)
        .filter((month) => !loadedMonths.has(month));

      const results = await Promise.all(
        unloaded.map(async (month) => {
          try {
            const res = await fetch(`/events/archive/archive-${month}.json`);
            if (!res.ok) return [];
            return res.json() as Promise<Event[]>;
          } catch {
            return [];
          }
        })
      );

      const allNewEvents = results.flat();
      setArchiveEvents((prev) => {
        const slugs = new Set(prev.map((e) => e.slug));
        const newEvents = allNewEvents.filter((e) => !slugs.has(e.slug));
        return [...prev, ...newEvents];
      });

      setLoadedMonths(new Set(archiveIndex.months.map((m) => m.month)));
    } catch (err) {
      console.error("Failed to load all archive months:", err);
    } finally {
      setLoading(false);
    }
  }, [archiveIndex, loadedMonths]);

  // Load only archive months that overlap with a date range
  const loadMonthsForRange = useCallback(async (startDate: string, endDate: string | null) => {
    if (!archiveIndex) return;

    // Get today in YYYY-MM-DD format for default end date
    const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });

    // Extract month strings (YYYY-MM)
    const startMonth = startDate.slice(0, 7);
    const endMonth = (endDate || today).slice(0, 7);

    // Find months in range that exist in archive and aren't loaded yet
    const monthsToLoad = archiveIndex.months
      .map((m) => m.month)
      .filter((month) => month >= startMonth && month <= endMonth)
      .filter((month) => !loadedMonths.has(month));

    if (monthsToLoad.length === 0) return;

    setLoading(true);
    try {
      const results = await Promise.all(
        monthsToLoad.map(async (month) => {
          try {
            const res = await fetch(`/events/archive/archive-${month}.json`);
            if (!res.ok) return [];
            return res.json() as Promise<Event[]>;
          } catch {
            return [];
          }
        })
      );

      const allNewEvents = results.flat();
      setArchiveEvents((prev) => {
        const slugs = new Set(prev.map((e) => e.slug));
        const newEvents = allNewEvents.filter((e) => !slugs.has(e.slug));
        return [...prev, ...newEvents];
      });

      setLoadedMonths((prev) => new Set([...prev, ...monthsToLoad]));
    } catch (err) {
      console.error("Failed to load archive months for range:", err);
    } finally {
      setLoading(false);
    }
  }, [archiveIndex, loadedMonths]);

  return {
    archiveIndex,
    archiveEvents,
    loadMonth,
    loadAllMonths,
    loadMonthsForRange,
    loading,
    loadedMonths,
  };
}
