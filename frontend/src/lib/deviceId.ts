const STORAGE_KEY = "taptot_device_id";

function newUuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback RFC4122-ish v4
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/** Stable per-browser device id for free-gen daily caps. */
export function getOrCreateDeviceId(): string {
  if (typeof window === "undefined") return newUuid();
  try {
    const existing = window.localStorage.getItem(STORAGE_KEY)?.trim();
    if (
      existing &&
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
        existing,
      )
    ) {
      return existing.toLowerCase();
    }
    const id = newUuid().toLowerCase();
    window.localStorage.setItem(STORAGE_KEY, id);
    return id;
  } catch {
    return newUuid().toLowerCase();
  }
}
