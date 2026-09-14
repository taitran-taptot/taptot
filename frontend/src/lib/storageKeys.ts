/** Migrate a storage item from an old key to a new key once. */
export function migrateItem(store: Storage, oldKey: string, newKey: string): void {
  if (store.getItem(newKey) != null) {
    store.removeItem(oldKey);
    return;
  }
  const value = store.getItem(oldKey);
  if (value != null) {
    store.setItem(newKey, value);
    store.removeItem(oldKey);
  }
}

export function migrateLocalKeys(pairs: Array<[oldKey: string, newKey: string]>): void {
  if (typeof window === "undefined") return;
  try {
    for (const [oldKey, newKey] of pairs) migrateItem(window.localStorage, oldKey, newKey);
  } catch {
    /* ignore */
  }
}

export function migrateSessionKeys(pairs: Array<[oldKey: string, newKey: string]>): void {
  if (typeof window === "undefined") return;
  try {
    for (const [oldKey, newKey] of pairs) migrateItem(window.sessionStorage, oldKey, newKey);
  } catch {
    /* ignore */
  }
}
