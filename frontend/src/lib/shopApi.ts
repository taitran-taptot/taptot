import { API_BASE } from "./config";
import { apiFetch } from "./http";
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
  price_vnd: number;
  stock_qty: number;
  image_url?: string | null;
  slug?: string | null;
  is_active?: boolean;
};

export const shopApi = {
  listProducts: (page = 1, pageSize = 24) =>
    apiFetch<Paginated<ShopProduct>>(`/shop/products?page=${page}&page_size=${pageSize}`),
  getPaymentInfo: () =>
    apiFetch<{
      bank_name?: string | null;
      bank_bin?: string | null;
      account_number?: string | null;
      account_name?: string | null;
      shipping_fee_vnd: number;
    }>("/shop/payment-info"),
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
  checkout: (body: ShopCheckoutPayload) =>
    apiFetch<ShopOrder>("/shop/orders", { method: "POST", body: JSON.stringify(body) }, {
      auth: false,
    }),
  trackOrder: (phone: string, public_code: string) =>
    apiFetch<ShopOrder>(
      "/shop/orders/track",
      { method: "POST", body: JSON.stringify({ phone, public_code }) },
      { auth: false },
    ),
  trackOrdersByPhone: (phone: string) =>
    apiFetch<{ items: ShopOrder[] }>(
      "/shop/orders/track",
      { method: "POST", body: JSON.stringify({ phone }) },
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
  adminListOrders: (p: { page?: number; order_status?: string } = {}) =>
    apiFetch<Paginated<ShopOrder>>(
      `/admin/shop/orders${qs({ page: p.page, page_size: 20, order_status: p.order_status })}`,
      {},
      auth,
    ),
  adminCancelOrder: (id: number) =>
    apiFetch<ShopOrder>(
      `/admin/shop/orders/${id}`,
      { method: "PATCH", body: JSON.stringify({ order_status: "cancelled" }) },
      auth,
    ),
  adminUpdateOrderStatus: (id: number, order_status: string) =>
    apiFetch<ShopOrder>(
      `/admin/shop/orders/${id}`,
      { method: "PATCH", body: JSON.stringify({ order_status }) },
      auth,
    ),
  adminActivationCoversUrl: (orderId: number) =>
    `${API_BASE}/admin/shop/orders/${orderId}/activation-covers.pdf`,
  adminDownloadActivationCovers: async (orderId: number, filename?: string) => {
    const res = await fetch(`${API_BASE}/admin/shop/orders/${orderId}/activation-covers.pdf`, {
      credentials: "include",
      headers: { Accept: "application/pdf" },
    });
    if (!res.ok) throw new Error("Không in được bìa kích hoạt.");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || `bia-don-${orderId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

export type RedeemLookup = {
  valid: boolean;
  status: string;
  product_name_vi?: string | null;
  code?: string | null;
};

export type RedeemCodeRow = {
  id: number;
  batch_id: number;
  code: string;
  status: string;
  redeemed_at?: string | null;
  plan_id?: number | null;
  share_url_path?: string | null;
  qr_data_uri?: string;
};

export type RedeemBatch = {
  id: number;
  product_id?: number | null;
  product_name_vi?: string | null;
  qty: number;
  unused_count?: number;
  note?: string | null;
  created_at?: string | null;
  codes?: RedeemCodeRow[];
};

export const redeemCodeApi = {
  lookup: (code: string) =>
    apiFetch<RedeemLookup>(`/shop/redeem-codes/lookup?code=${encodeURIComponent(code)}`),
  adminListBatches: (page = 1) =>
    apiFetch<Paginated<RedeemBatch>>(`/shop/redeem-codes/batches?page=${page}&page_size=20`, {}, auth),
  adminCreateBatch: (body: { product_id?: number | null; qty: number; note?: string | null }) =>
    apiFetch<RedeemBatch>("/shop/redeem-codes/batches", { method: "POST", body: JSON.stringify(body) }, auth),
  adminListCodes: (p: { page?: number; batch_id?: number; status?: string } = {}) =>
    apiFetch<Paginated<RedeemCodeRow>>(
      `/shop/redeem-codes${qs({ page: p.page, page_size: 50, batch_id: p.batch_id, status: p.status })}`,
      {},
      auth,
    ),
  adminVoid: (id: number) =>
    apiFetch<RedeemCodeRow>(`/shop/redeem-codes/${id}/void`, { method: "POST" }, auth),
  adminPrintHtml: async (batchId: number) => {
    const res = await fetch(`${API_BASE}/shop/redeem-codes/batches/${batchId}/print`, {
      headers: { Accept: "text/html" },
      credentials: "include",
    });
    if (!res.ok) throw new Error("Không in được tem.");
    return res.text();
  },
};

export async function uploadAdminMedia(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const headers: Record<string, string> = { Accept: "application/json" };
  const res = await fetch(`${API_BASE}/media/upload`, { method: "POST", headers, body: form, credentials: "include" });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = (data as { detail?: string }).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : "Upload thất bại");
  }
  const data = (await res.json()) as { url?: string };
  if (!data.url) throw new Error("Upload không trả về URL");
  return data.url;
}
