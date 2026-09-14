import { migrateLocalKeys } from "./storageKeys";

const TOKEN_KEY = "taptot_access_token";
const REFRESH_KEY = "taptot_refresh_token";
const USER_KEY = "taptot_user";
const TFIT_TOKEN_KEY = "tfit_access_token";
const TFIT_REFRESH_KEY = "tfit_refresh_token";
const TFIT_USER_KEY = "tfit_user";
const VIETFIT_TOKEN_KEY = "vietfit_access_token";
const VIETFIT_REFRESH_KEY = "vietfit_refresh_token";
const VIETFIT_USER_KEY = "vietfit_user";

migrateLocalKeys([
  [TFIT_TOKEN_KEY, TOKEN_KEY],
  [TFIT_REFRESH_KEY, REFRESH_KEY],
  [TFIT_USER_KEY, USER_KEY],
  [VIETFIT_TOKEN_KEY, TOKEN_KEY],
  [VIETFIT_REFRESH_KEY, REFRESH_KEY],
  [VIETFIT_USER_KEY, USER_KEY],
]);

export interface AuthUser {
  id: string;
  email: string | null;
  display_name: string | null;
  role: string;
  email_verified: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

export function getAccessToken(): string | null {
  return storage()?.getItem(TOKEN_KEY) ?? null;
}

export function getRefreshToken(): string | null {
  return storage()?.getItem(REFRESH_KEY) ?? null;
}

export function getStoredUser(): AuthUser | null {
  const raw = storage()?.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function saveAuth(tokens: TokenPair, user?: AuthUser) {
  const s = storage();
  if (!s) return;
  s.setItem(TOKEN_KEY, tokens.access_token);
  s.setItem(REFRESH_KEY, tokens.refresh_token);
  if (user) s.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  const s = storage();
  if (!s) return;
  s.removeItem(TOKEN_KEY);
  s.removeItem(REFRESH_KEY);
  s.removeItem(USER_KEY);
  s.removeItem(TFIT_TOKEN_KEY);
  s.removeItem(TFIT_REFRESH_KEY);
  s.removeItem(TFIT_USER_KEY);
  s.removeItem(VIETFIT_TOKEN_KEY);
  s.removeItem(VIETFIT_REFRESH_KEY);
  s.removeItem(VIETFIT_USER_KEY);
}

export function authHeaders(): Record<string, string> {
  const t = getAccessToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}
