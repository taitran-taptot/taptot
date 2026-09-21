import { API_BASE } from "./config";
import { clearAuth, isAuthenticated } from "./auth";
import { requestAdminStepUp } from "./adminStepUp";

export const LOGOUT_EVENT = "taptot:logout";
export const AUTH_EVENT = "taptot:auth";

let handlingUnauthorized = false;
let refreshInFlight: Promise<boolean> | null = null;

/** Clear session and redirect when API returns 401. */
export function handleUnauthorized(message = "Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại."): void {
  if (typeof window === "undefined") return;
  if (handlingUnauthorized) return;
  handlingUnauthorized = true;
  try {
    clearAuth();
    window.dispatchEvent(new CustomEvent(LOGOUT_EVENT, { detail: { message } }));
    const path = window.location.pathname + window.location.search;
    const needsLogin =
      path.startsWith("/tai-khoan") ||
      path.startsWith("/gop-y") ||
      path.startsWith("/gio-hang");
    if (needsLogin) {
      const next = encodeURIComponent(path.startsWith("/dang-nhap") ? "/tai-khoan/ke-hoach" : path);
      window.location.href = `/dang-nhap?next=${next}`;
    } else {
      window.location.reload();
    }
  } finally {
    setTimeout(() => {
      handlingUnauthorized = false;
    }, 1500);
  }
}

export function errorMessage(data: unknown, fallback: string): string {
  const detail = (data as { detail?: unknown; message?: unknown })?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ") || fallback;
  }
  if (typeof detail === "string") return detail;
  const msg = (data as { message?: unknown })?.message;
  if (typeof msg === "string") return msg;
  return fallback;
}

export type FetchOpts = {
  auth?: boolean;
  requireAuth?: boolean;
  baseUrl?: string;
  _retried?: boolean;
  _stepUpRetried?: boolean;
};

async function tryRefresh(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE.replace(/\/$/, "")}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

/** Shared fetch: cookies for session; auto-logout on 401. */
export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  opts: FetchOpts = {},
): Promise<T> {
  const auth = !!opts.auth;
  const requireAuth = opts.requireAuth ?? auth;
  const base = (opts.baseUrl || API_BASE).replace(/\/$/, "");

  if (requireAuth && typeof window !== "undefined" && !isAuthenticated() && path !== "/auth/me") {
    throw new Error("Vui lòng đăng nhập.");
  }

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (init.body && !headers["Content-Type"] && !(init.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let res: Response;
  try {
    res = await fetch(`${base}${path}`, { ...init, headers, credentials: "include" });
  } catch {
    throw new Error(
      `Không kết nối được API (${base}). Kiểm tra backend đang chạy (cổng 8000) rồi thử lại.`,
    );
  }

  if (res.status === 401 && auth && !opts._retried) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return apiFetch<T>(path, init, { ...opts, _retried: true });
    }
    if (requireAuth || isAuthenticated()) {
      handleUnauthorized();
      throw new Error("Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.");
    }
    throw new Error(errorMessage(await res.json().catch(() => ({})), "Yêu cầu thất bại"));
  }

  if (res.status === 403 && !opts._stepUpRetried) {
    const data = await res.clone().json().catch(() => ({}));
    if ((data as { code?: string }).code === "admin_step_up") {
      const ok = await requestAdminStepUp();
      if (ok) {
        return apiFetch<T>(path, init, { ...opts, _stepUpRetried: true });
      }
    }
  }

  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const fallback =
      res.status === 500 || /internal server error/i.test(res.statusText || "")
        ? "Không tạo được lịch lúc này (máy chủ phản hồi chậm hoặc lỗi tạm). Thử lại sau vài giây."
        : res.statusText || "Yêu cầu thất bại";
    throw new Error(errorMessage(data, fallback));
  }
  return data as T;
}
