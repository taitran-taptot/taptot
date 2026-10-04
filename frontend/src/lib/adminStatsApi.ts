import { apiFetch } from "./http";

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
};

export function adminGetStats(year?: number) {
  const qs = year ? `?year=${year}` : "";
  return apiFetch<AdminStatsResponse>(`/admin/stats${qs}`, {}, { auth: true });
}
