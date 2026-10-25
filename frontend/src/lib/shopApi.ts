import { API_BASE } from "./config";
import { apiFetch } from "./http";
import { storedMediaPath } from "./labels";
import type { Paginated, ShopCart, ShopCheckoutPayload, ShopOrder, ShopProduct } from "./types";

const auth = { auth: true as const };

function qs(p: Record<string, string | number | undefined>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) {
    if (v === undefined || v === "") continue;
    u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

export type ShopProductPayload = {
  name_vi: string;
  description_vi?: string | null;
  usage_vi?: string | null;
  gallery_urls?: string[];
  youtube_url?: string | null;
  price_vnd: number;
  stock_qty: number;
  image_url?: string | null;
  slug?: string | null;
  is_active?: boolean;
};

export const shopApi = {
  listProducts: (page = 1, pageSize = 24) =>
    apiFetch<Paginated<ShopProduct>>(`/shop/products?page=${page}&page_size=${pageSize}`),
  getProductBySlug: (slug: string) =>
    apiFetch<ShopProduct>(`/shop/products/slug/${encodeURIComponent(slug)}`, {}, { auth: false, requireAuth: false }),
  getCart: () => apiFetch<ShopCart>("/shop/cart", {}, auth),
  addToCart: (product_id: number, quantity = 1) =>
    apiFetch<ShopCart>(
      "/shop/cart/items",
      { method: "POST", body: JSON.stringify({ product_id, quantity }) },
      auth,
    ),
  mergeCart: (items: { product_id: number; quantity: number }[]) =>
    apiFetch<ShopCart>(
      "/shop/cart/merge",
      { method: "POST", body: JSON.stringify({ items }) },
      auth,
    ),
  setCartQty: (product_id: number, quantity: number) =>
    apiFetch<ShopCart>(
      `/shop/cart/items/${product_id}`,
      { method: "PATCH", body: JSON.stringify({ quantity }) },
      auth,
    ),
  checkout: (body: ShopCheckoutPayload, idempotencyKey: string) =>
    apiFetch<ShopOrder>(
      "/shop/orders",
      {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify(body),
      },
      { auth: false },
    ),
  trackOrder: (phone: string, public_code: string) =>
    apiFetch<ShopOrder>(
      "/shop/orders/track",
      { method: "POST", body: JSON.stringify({ phone, public_code }) },
      { auth: false },
    ),
  adminListProducts: (p: { page?: number; q?: string; is_active?: string } = {}) =>
    apiFetch<Paginated<ShopProduct>>(
      `/admin/shop/products${qs({ page: p.page, page_size: 20, q: p.q, is_active: p.is_active })}`,
      {},
      auth,
    ),
  adminCreateProduct: (body: ShopProductPayload) =>
    apiFetch<ShopProduct>("/admin/shop/products", { method: "POST", body: JSON.stringify(body) }, auth),
  adminUpdateProduct: (id: number, body: Partial<ShopProductPayload>) =>
    apiFetch<ShopProduct>(
      `/admin/shop/products/${id}`,
      { method: "PATCH", body: JSON.stringify(body) },
      auth,
    ),
  adminDeleteProduct: (id: number) =>
    apiFetch<void>(`/admin/shop/products/${id}`, { method: "DELETE" }, auth),
  adminListOrders: (
    p: {
      page?: number;
      page_size?: number;
      order_status?: string;
      created_from?: string;
      created_to?: string;
    } = {},
  ) =>
    apiFetch<Paginated<ShopOrder>>(
      `/admin/shop/orders${qs({
        page: p.page,
        page_size: p.page_size ?? 20,
        order_status: p.order_status,
        created_from: p.created_from,
        created_to: p.created_to,
      })}`,
      {},
      auth,
    ),
  adminUpdateOrderStatus: (id: number, order_status: string) =>
    apiFetch<ShopOrder>(
      `/admin/shop/orders/${id}`,
      { method: "PATCH", body: JSON.stringify({ order_status }) },
      auth,
    ),
  adminBulkUpdateOrderStatus: (orderIds: number[], order_status: string) =>
    apiFetch<{
      updated_count: number;
      skipped_count: number;
      error_count: number;
      updated_ids: number[];
      skipped_ids: number[];
      errors: { id: number; message: string }[];
    }>(
      "/admin/shop/orders/bulk-status",
      { method: "POST", body: JSON.stringify({ order_ids: orderIds, order_status }) },
      auth,
    ),
  adminDownloadActivationCovers: async (orderId: number, filename?: string) => {
    const res = await fetch(`${API_BASE}/admin/shop/orders/${orderId}/activation-covers.pdf`, {
      credentials: "include",
      headers: { Accept: "application/pdf" },
    });
    if (!res.ok) throw new Error("Không in được bìa kích hoạt.");
    await _savePdf(res, filename || `bia-don-${orderId}.pdf`);
  },
  adminDownloadBulkActivationCovers: async (orderIds: number[], filename?: string) => {
    const res = await fetch(`${API_BASE}/admin/shop/orders/activation-covers.pdf`, {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/pdf", "Content-Type": "application/json" },
      body: JSON.stringify({ order_ids: orderIds }),
    });
    if (!res.ok) throw new Error("Không in được bìa hàng loạt.");
    await _savePdf(res, filename || "bia-hang-loat.pdf");
  },
};

async function _savePdf(res: Response, filename: string) {
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export type RedeemLookup = {
  valid: boolean;
  status: string;
  product_name_vi?: string | null;
  code?: string | null;
};

export const redeemCodeApi = {
  lookup: (code: string) =>
    apiFetch<RedeemLookup>(`/shop/redeem-codes/lookup?code=${encodeURIComponent(code)}`),
};

export async function uploadAdminMedia(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const data = await apiFetch<{ url?: string }>("/media/upload", { method: "POST", body: form }, { auth: true });
  if (!data.url) throw new Error("Upload không trả về URL");
  return storedMediaPath(data.url);
}
