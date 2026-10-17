import { apiFetch } from "./http";

export type ShopStatsBucket = {
  period: string;
  orders: number;
  cancelled: number;
  units: number;
  gross_vnd: number;
  discount_vnd: number;
  net_vnd: number;
  collected_vnd: number;
  shipping_vnd: number;
  units_by_slug: Record<string, number>;
};

export type ShopProductStats = {
  slug: string;
  name_vi: string;
  units: number;
  line_vnd: number;
  order_count: number;
  stock_qty: number;
};

export type ShopStats = {
  grain: "month" | "day";
  kpis: {
    orders: number;
    cancelled: number;
    units: number;
    gross_vnd: number;
    discount_vnd: number;
    net_vnd: number;
    collected_vnd: number;
    shipping_vnd: number;
    aov_vnd: number;
    cancel_rate: number;
    discount_orders: number;
    discount_order_rate: number;
    repeat_customers: number;
    unique_customers: number;
  };
  products: ShopProductStats[];
  series: ShopStatsBucket[];
  funnel: Record<string, number>;
  payments: Record<string, number>;
  pushup: {
    sessions_completed: number;
    discount_orders: number;
    discount_vnd: number;
    by_percent: Record<string, number>;
  };
};

export type AdminStatsMonth = {
  month: string;
  plans: {
    generated: number;
    admin_created: number;
    hlv_created: number;
    templates: number;
    challenge_100: number;
    guest: number;
  };
  orders: {
    count: number;
    gmv_vnd: number;
    collected_vnd: number;
    by_status: Record<string, number>;
    by_payment_method: Record<string, number>;
  };
  users: { new: number; staff: number };
  challenge: { paid_count: number; paid_vnd: number };
  redeem: { used: number };
};

export type AdminStatsResponse = {
  year: number;
  month: number | null;
  kpis: {
    plans_generated: number;
    plans_admin_created: number;
    plans_hlv_created: number;
    orders_count: number;
    orders_gmv_vnd: number;
    orders_collected_vnd: number;
    users_new: number;
    challenge_paid_vnd: number;
    redeem_used: number;
    redeem_unused: number;
    pushup_completed: number;
  };
  months: AdminStatsMonth[];
  hlv_accounts: {
    user_id: string;
    email: string | null;
    display_name: string | null;
    total: number;
    generated: number;
    manual: number;
    template: number;
    imported: number;
  }[];
  open_orders: {
    awaiting_confirm: number;
    awaiting_transfer: number;
  };
  shop: ShopStats;
};

export function adminGetStats(year?: number, month?: number | null) {
  const u = new URLSearchParams();
  if (year) u.set("year", String(year));
  if (month) u.set("month", String(month));
  const qs = u.toString() ? `?${u}` : "";
  return apiFetch<AdminStatsResponse>(`/admin/stats${qs}`, {}, { auth: true });
}
