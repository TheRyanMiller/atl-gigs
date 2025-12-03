import { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef, ReactNode } from "react";

const STORAGE_KEY = "atl-gigs-favorites";

interface FavoritesContextType {
  favorites: Set<string>;
  toggleFavorite: (slug: string) => void;
  isFavorite: (slug: string) => boolean;
  clearFavorites: () => void;
  favoriteCount: number;
}

const FavoritesContext = createContext<FavoritesContextType | null>(null);

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const [favorites, setFavorites] = useState<Set<string>>(() => {
    // Initialize from localStorage
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return new Set(Array.isArray(parsed) ? parsed : []);
      }
    } catch (e) {
      console.error("Failed to load favorites from localStorage:", e);
    }
    return new Set();
  });

  // Keep a ref to the current favorites for sync access in isFavorite
  const favoritesRef = useRef(favorites);
  favoritesRef.current = favorites;

  // Debounce localStorage writes to avoid blocking UI
  const saveTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    // Clear any pending save
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    // Schedule async save
    saveTimeoutRef.current = window.setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify([...favorites]));
      } catch (e) {
        console.error("Failed to save favorites to localStorage:", e);
      }
    }, 100);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [favorites]);

  const toggleFavorite = useCallback((slug: string) => {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) {
        next.delete(slug);
      } else {
        next.add(slug);
      }
      return next;
    });
  }, []);

  // Stable isFavorite that uses ref - doesn't recreate on favorites change
  const isFavorite = useCallback((slug: string) => favoritesRef.current.has(slug), []);

  const clearFavorites = useCallback(() => {
    setFavorites(new Set());
  }, []);

  const value = useMemo(
    () => ({
      favorites,
      toggleFavorite,
      isFavorite,
      clearFavorites,
      favoriteCount: favorites.size,
    }),
    [favorites, toggleFavorite, isFavorite, clearFavorites]
  );

  return (
    <FavoritesContext.Provider value={value}>
      {children}
    </FavoritesContext.Provider>
  );
}

export function useFavorites() {
  const context = useContext(FavoritesContext);
  if (!context) {
    throw new Error("useFavorites must be used within a FavoritesProvider");
  }
  return context;
}
