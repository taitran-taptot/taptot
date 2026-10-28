"use client";

import { useEffect, useState } from "react";
import CollaboratorStatsPanel from "./CollaboratorStatsPanel";
import { collaboratorApi, type CollaboratorAccount } from "@/lib/collaboratorApi";
import { formatVnd } from "@/lib/labels";

export default function CollaboratorPromoPanel() {
  const [account, setAccount] = useState<CollaboratorAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    collaboratorApi
      .mine(1, 1)
      .then((data) => {
        if (cancelled) return;
        setAccount(data);
        setError("");
        setLoading(false);
      })
      .catch((ex: unknown) => {
        if (cancelled) return;
        setError(ex instanceof Error ? ex.message : "Không tải được mã giảm giá");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function copyCode(code: string) {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="space-y-4">
      {loading ? (
        <p className="text-sm text-slate-400">Đang tải…</p>
      ) : (
        <section className="rounded-2xl bg-white p-5 shadow-soft">
          <h1 className="type-display">Mã giảm giá</h1>
          <p className="mt-1 text-sm text-slate-500">
            Mã do admin tạo. Mức giảm hiện là {account?.discount_percent ?? 0}%.
          </p>
          {error && <p className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>}
          {account?.code ? (
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <p className="font-mono text-lg font-bold text-brand-700">{account.code}</p>
              <button
                type="button"
                onClick={() => void copyCode(account.code!)}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                {copied ? "Đã chép" : "Chép mã"}
              </button>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">Admin chưa tạo mã cho tài khoản này.</p>
          )}
          <p className="mt-4 text-sm text-slate-600">
            {account?.order_count ?? 0} đơn đã dùng mã · tổng đã giảm {formatVnd(account?.discount_vnd || 0)}
          </p>
        </section>
      )}
      <CollaboratorStatsPanel />
    </div>
  );
}
