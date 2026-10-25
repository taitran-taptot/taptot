const STORAGE_KEY = "taptot.shop.checkout-idempotency.v1";

type StoredCheckoutKey = {
  key: string;
  fingerprint: string;
};

let memoryEntry: StoredCheckoutKey | null = null;

function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, item]) => [key, stableValue(item)]),
    );
  }
  return value;
}

function fingerprint(payload: unknown): string {
  const input = JSON.stringify(stableValue(payload));
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function newKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const bytes = new Uint8Array(16);
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < bytes.length; i += 1) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}

export function checkoutIdempotencyKey(payload: unknown): string {
  const nextFingerprint = fingerprint(payload);
  if (typeof window !== "undefined") {
    try {
      const parsed = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null") as StoredCheckoutKey | null;
      if (parsed?.key && parsed.fingerprint === nextFingerprint) return parsed.key;
      const key = newKey();
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ key, fingerprint: nextFingerprint }));
      return key;
    } catch {
      // Storage can be blocked; fall back to the in-memory entry below.
    }
  }
  if (memoryEntry?.fingerprint === nextFingerprint) return memoryEntry.key;
  const key = newKey();
  memoryEntry = { key, fingerprint: nextFingerprint };
  return key;
}

export function clearCheckoutIdempotencyKey(key: string): void {
  if (memoryEntry?.key === key) memoryEntry = null;
  if (typeof window === "undefined") return;
  try {
    const parsed = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null") as StoredCheckoutKey | null;
    if (parsed?.key === key) sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore unavailable/corrupt storage.
  }
}
