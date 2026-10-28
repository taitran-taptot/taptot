import { apiFetch } from "./http";

const auth = { auth: true as const };

export type PromoOrderItem = {
  id: number;
  name_vi: string;
  quantity: number;
  line_total_vnd: number;
};

export type PromoOrder = {
  id: number;
  public_code?: string | null;
  order_status: string;
  created_at?: string | null;
  recipient_name?: string | null;
  province_name?: string | null;
  district_name?: string | null;
  phone?: string | null;
  ward_name?: string | null;
  address_line?: string | null;
  total_vnd: number;
  discount_percent?: number;
  discount_vnd?: number;
  promo_code?: string | null;
  promo_percent?: number;
  promo_discount_vnd?: number;
  items: PromoOrderItem[];
};

export type PromoOrderPage = {
  items: PromoOrder[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type CollaboratorAccount = {
  id: string;
  email: string | null;
  display_name: string | null;
  role: string;
  code: string | null;
  discount_percent: number;
  order_count: number;
  discount_vnd: number;
  created_at?: string | null;
  orders?: PromoOrderPage;
};

function qs(page: number, pageSize: number) {
  return `?page=${page}&page_size=${pageSize}`;
}

export const collaboratorApi = {
  adminList: () => apiFetch<{ items: CollaboratorAccount[] }>("/admin/collaborators", {}, auth),
  adminCreate: (body: {
    email: string;
    password: string;
    display_name: string;
    discount_percent: number;
  }) =>
    apiFetch<CollaboratorAccount>(
      "/admin/collaborators",
      { method: "POST", body: JSON.stringify(body) },
      auth,
    ),
  adminUpdate: (
    userId: string,
    body: {
      display_name?: string;
      email?: string;
      password?: string;
      discount_percent?: number;
    },
  ) =>
    apiFetch<CollaboratorAccount>(
      `/admin/collaborators/${userId}`,
      { method: "PATCH", body: JSON.stringify(body) },
      auth,
    ),
  adminDelete: (userId: string) =>
    apiFetch<void>(`/admin/collaborators/${userId}`, { method: "DELETE" }, auth),
  adminCreateCode: (userId: string, code: string) =>
    apiFetch<{ code: string; discount_percent: number }>(
      `/admin/collaborators/${userId}/code`,
      { method: "POST", body: JSON.stringify({ code }) },
      auth,
    ),
  adminOrders: (userId: string, page = 1, pageSize = 20) =>
    apiFetch<PromoOrderPage>(`/admin/collaborators/${userId}/orders${qs(page, pageSize)}`, {}, auth),
  mine: (page = 1, pageSize = 10) =>
    apiFetch<CollaboratorAccount>(`/collaborator/promo${qs(page, pageSize)}`, {}, auth),
  stats: (
    period: "day" | "month" | "year",
    on: string,
    page = 1,
    pageSize = 10,
    q = "",
    sort: "asc" | "desc" = "desc",
    status = "",
  ) =>
    apiFetch<CollaboratorPeriodStats>(
      `/collaborator/promo/stats?period=${encodeURIComponent(period)}&on=${encodeURIComponent(on)}&page=${page}&page_size=${pageSize}&q=${encodeURIComponent(q)}&sort=${sort}&status=${encodeURIComponent(status)}`,
      {},
      auth,
    ),
};

export type CollaboratorPeriodStats = {
  period: "day" | "month" | "year";
  label: string;
  order_count: number;
  total_vnd: number;
  discount_vnd: number;
  orders: PromoOrderPage;
};
