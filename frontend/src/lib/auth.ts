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

const ACCOUNT_ROLES = new Set(["admin", "hlv", "ctv"]);

export function isAccountRole(role?: string | null): boolean {
  return ACCOUNT_ROLES.has(role || "");
}

export function getStoredUser(): AuthUser | null {
  const store = sessionStore();
  const raw = store?.getItem(USER_KEY);
  if (!raw) return null;
  try {
    const user = JSON.parse(raw) as AuthUser;
    if (!isAccountRole(user.role)) {
      store?.removeItem(USER_KEY);
      return null;
    }
    return user;
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

export function isAdmin(role?: string | null): boolean {
  return role === "admin";
}

export function isHlv(role?: string | null): boolean {
  return role === "hlv";
}

export function isCtv(role?: string | null): boolean {
  return role === "ctv";
}

export function isStaff(role?: string | null): boolean {
  return role === "admin" || role === "hlv";
}

export function clearAuth() {
  sessionStore()?.removeItem(USER_KEY);
  const local = localStore();
  if (!local) return;
  for (const key of LEGACY_TOKEN_KEYS) local.removeItem(key);
  local.removeItem(USER_KEY);
}
