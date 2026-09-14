import { API_BASE } from "./config";
import { authHeaders, clearAuth, getAccessToken } from "./auth";

export const LOGOUT_EVENT = "taptot:logout";

let handlingUnauthorized = false;

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
      path.startsWith("/hlv") ||
      path.startsWith("/gop-y") ||
      path.startsWith("/gio-hang") ||
      path.startsWith("/tai-khoan/gop-y");
    if (needsLogin && !path.startsWith("/hlv/p/")) {
      const next = encodeURIComponent(path.startsWith("/dang-nhap") ? "/tai-khoan" : path);
      window.location.href = `/dang-nhap?next=${next}`;
    } else {
      // Stay on public page but force UI refresh so auth menus clear
      window.location.reload();
    }
  } finally {
    // allow future 401s after navigation settles
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
  /** If true, missing token throws before request. Default = auth */
  requireAuth?: boolean;
  /** Override API root (e.g. absolute FastAPI URL for long-running calls). */
  baseUrl?: string;
};

/** Shared fetch: auto-logout on 401 when the request used auth. */
export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  opts: FetchOpts = {},
): Promise<T> {
  const auth = !!opts.auth;
  const requireAuth = opts.requireAuth ?? auth;
  const base = (opts.baseUrl || API_BASE).replace(/\/$/, "");

  if (requireAuth && !getAccessToken()) {
    throw new Error("Vui lòng đăng nhập.");
  }

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (auth) Object.assign(headers, authHeaders());
  if (init.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  let res: Response;
  try {
    res = await fetch(`${base}${path}`, { ...init, headers });
  } catch {
    throw new Error(
      `Không kết nối được API (${base}). Kiểm tra backend đang chạy (cổng 8000) rồi thử lại.`,
    );
  }

  if (res.status === 401 && auth) {
    // Only force-logout when the call required a session (avoid guest AI 401 loops).
    if (requireAuth || getAccessToken()) {
      handleUnauthorized();
      throw new Error("Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.");
    }
    throw new Error(errorMessage(await res.json().catch(() => ({})), "Yêu cầu thất bại"));
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
