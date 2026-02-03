import "@testing-library/jest-dom";

class LocalStorageMock {
  private store: Record<string, string> = {};

  clear() {
    this.store = {};
  }

  getItem(key: string) {
    return this.store[key] ?? null;
  }

  setItem(key: string, value: string) {
    this.store[key] = value;
  }

  removeItem(key: string) {
    delete this.store[key];
  }
}

if (!window.localStorage || typeof window.localStorage.getItem !== "function") {
  Object.defineProperty(window, "localStorage", {
    value: new LocalStorageMock(),
    writable: true,
  });
}
