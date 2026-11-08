import { apiFetch } from "./http";

export type AdminStatsResponse = {
  year: number;
  month: number | null;
  finance: FinanceBoard;
  inventory: InventoryBoard;
};

export type InventoryProduct = {
  id: number;
  name_vi: string;
  total: number;
  sold: number;
  remaining: number;
};

export type InventoryBoard = {
  totals: {
    total: number;
    sold: number;
    remaining: number;
  };
  products: InventoryProduct[];
};

export type FinanceProductMonth = {
  month: number;
  units: number;
  revenue_vnd: number;
  profit_vnd: number;
};

export type FinanceProduct = {
  id: number;
  slug: string;
  name_vi: string;
  months: FinanceProductMonth[];
};

export type FinanceMonth = {
  month: number;
  revenue_vnd: number;
  units_by_product: { product_id: number; units: number }[];
  costs: {
    operating_vnd: number;
    marketing_vnd: number;
    product_costs: { product_id: number; cost_vnd: number }[];
  };
  cogs_vnd: number;
  profit_vnd: number;
};

export type FinanceBoard = {
  lifetime: {
    revenue_vnd: number;
    profit_vnd: number;
    operating_vnd: number;
    marketing_vnd: number;
    orders: number;
    collected_vnd: number;
    uncollected_vnd: number;
  };
  products: FinanceProduct[];
  months: FinanceMonth[];
  order_status: {
    awaiting_confirm: number;
    packing: number;
    shipping: number;
    completed: number;
    cancelled: number;
    returned: number;
  };
};

export function adminGetStats(year?: number, month?: number | null) {
  const u = new URLSearchParams();
  if (year) u.set("year", String(year));
  if (month) u.set("month", String(month));
  const qs = u.toString() ? `?${u}` : "";
  return apiFetch<AdminStatsResponse>(`/admin/stats${qs}`, {}, { auth: true });
}

export function adminSetMonthCosts(payload: {
  year: number;
  month: number;
  operating_vnd: number;
  marketing_vnd: number;
  product_costs: { product_id: number; cost_vnd: number }[];
}) {
  return apiFetch<{
    year: number;
    month: number;
    operating_vnd: number;
    marketing_vnd: number;
    product_costs: { product_id: number; cost_vnd: number }[];
  }>(
    "/admin/stats/month-costs",
    { method: "PUT", body: JSON.stringify(payload) },
    { auth: true },
  );
}
