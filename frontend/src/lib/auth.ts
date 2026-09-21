export interface AuthUser {
  id: string;
  email: string | null;
  display_name: string | null;
  role: string;
  email_verified: boolean;
}

const USER_KEY = "taptot_user";
const LEGACY_TOKEN_KEYS = [
  "taptot_access_token",
  "taptot_refresh_token",
  "tfit_access_token",
  "tfit_refresh_token",
  "tfit_user",
  "vietfit_access_token",
  "vietfit_refresh_token",
  "vietfit_user",
];

function sessionStore(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage;
}

function localStore(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

export function getStoredUser(): AuthUser | null {
  const raw = sessionStore()?.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function saveUser(user: AuthUser | null) {
  const s = sessionStore();
  if (!s) return;
  if (user) s.setItem(USER_KEY, JSON.stringify(user));
  else s.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return getStoredUser() !== null;
}

export function clearAuth() {
  sessionStore()?.removeItem(USER_KEY);
  const local = localStore();
  if (!local) return;
  for (const key of LEGACY_TOKEN_KEYS) local.removeItem(key);
  local.removeItem(USER_KEY);
}
