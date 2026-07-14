const STORAGE_KEY = "levels:reduced-motion";

export type MotionPreference = boolean | null;

export function applyMotionPreference(preference: MotionPreference) {
  try {
    if (preference === null) {
      document.documentElement.removeAttribute("data-reduced-motion");
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    document.documentElement.dataset.reducedMotion = String(preference);
    localStorage.setItem(STORAGE_KEY, String(preference));
  } catch {
    // The OS media query remains authoritative when storage is unavailable.
  }
}

export function applyStoredMotionPreference() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "true" || stored === "false") {
      document.documentElement.dataset.reducedMotion = stored;
    }
  } catch {
    // Hardened browser modes can block storage without blocking the app.
  }
}
