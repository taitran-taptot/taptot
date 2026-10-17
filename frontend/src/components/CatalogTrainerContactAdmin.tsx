"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import {
  trainerContactAdminApi,
  type TrainerLead,
  type TrainerLeadStatus,
} from "@/lib/authApi";

const STATUSES: { id: TrainerLeadStatus; label: string }[] = [
  { id: "new", label: "Mới" },
  { id: "contacted", label: "Đã liên hệ" },
  { id: "won", label: "Chốt" },
  { id: "lost", label: "Không chốt" },
];

const PAGE_SIZES = [10, 20, 50, 100] as const;

function statusTone(status: string) {
  if (status === "won") return "bg-emerald-50 text-emerald-800";
  if (status === "lost") return "bg-rose-50 text-rose-700";
  if (status === "contacted") return "bg-sky-50 text-sky-800";
  return "bg-amber-50 text-amber-800";
}

function statusLabel(status: string) {
  return STATUSES.find((s) => s.id === status)?.label ?? status;
}

function zaloHref(phone: string): string | null {
  const digits = phone.replace(/\D/g, "");
  if (!digits) return null;
  const intl = digits.startsWith("84") ? digits : digits.startsWith("0") ? `84${digits.slice(1)}` : digits;
  return `https://zalo.me/${intl}`;
}

function formatWhen(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

function previewMessage(message: string | null) {
  if (!message) return "—";
  const first = message.split("\n").find((line) => line.trim()) || message;
  return first.length > 48 ? `${first.slice(0, 46)}…` : first;
}

export default function CatalogTrainerContactAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [items, setItems] = useState<TrainerLead[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [q, setQ] = useState("");
  const [qDraft, setQDraft] = useState("");
  const [filter, setFilter] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [noteDraft, setNoteDraft] = useState("");

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== "admin") {
      router.replace("/tai-khoan/ke-hoach");
      return;
    }
    setAllowed(true);
  }, [router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const d = await trainerContactAdminApi.list({
        page,
        page_size: pageSize,
        q: q || undefined,
        status: filter || undefined,
        created_from: fromDate || undefined,
        created_to: toDate || undefined,
      });
      setItems(d.items || []);
      setPages(d.pages || 1);
      setTotal(d.total || 0);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, q, filter, fromDate, toDate]);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  async function setStatus(id: number, status: TrainerLeadStatus) {
    setBusyId(id);
    setError("");
    try {
      await trainerContactAdminApi.patch(id, { status });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  async function saveNote(id: number) {
    setBusyId(id);
    setError("");
    try {
      await trainerContactAdminApi.patch(id, { admin_note: noteDraft });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  if (!allowed) return null;

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Đăng ký tư vấn</h1>
      <p className="mt-1 text-sm text-slate-500">
        Form /lien-he. Liên hệ Zalo, đổi trạng thái, ghi chú nội bộ.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setQ(qDraft.trim());
          }}
        >
          <input
            className="w-52 rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="Tên, SĐT, email…"
            value={qDraft}
            onChange={(e) => setQDraft(e.target.value)}
          />
          <button type="submit" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
            Tìm
          </button>
        </form>
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={filter}
          onChange={(e) => {
            setPage(1);
            setFilter(e.target.value);
          }}
        >
          <option value="">Tất cả</option>
          {STATUSES.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-sm text-slate-600">
          Từ
          <input
            type="date"
            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
            value={fromDate}
            onChange={(e) => {
              setPage(1);
              setFromDate(e.target.value);
            }}
          />
        </label>
        <label className="flex items-center gap-1.5 text-sm text-slate-600">
          Đến
          <input
            type="date"
            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
            value={toDate}
            onChange={(e) => {
              setPage(1);
              setToDate(e.target.value);
            }}
          />
        </label>
        <label className="ml-auto flex items-center gap-2 text-sm text-slate-600">
          Hiển thị
          <select
            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
            value={pageSize}
            onChange={(e) => {
              setPage(1);
              setPageSize(Number(e.target.value));
            }}
          >
            {PAGE_SIZES.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          / trang
        </label>
      </div>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
        {loading ? (
          <p className="px-4 py-6 text-sm text-slate-400">Đang tải…</p>
        ) : items.length === 0 ? (
          <p className="px-4 py-6 text-slate-400">Chưa có đăng ký.</p>
        ) : (
          <ul>
            {items.map((row) => {
              const open = openId === row.id;
              const zalo = zaloHref(row.phone_zalo);
              return (
                <li key={row.id} className="border-b border-slate-100 last:border-b-0">
                  <button
                    type="button"
                    className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-slate-50"
                    onClick={() => {
                      setOpenId(open ? null : row.id);
                      setNoteDraft(row.admin_note || "");
                    }}
                    aria-expanded={open}
                  >
                    <span className="w-36 shrink-0 text-xs text-slate-500">{formatWhen(row.created_at)}</span>
                    <span className="w-40 shrink-0 truncate text-sm font-semibold text-slate-800">
                      {row.full_name}
                    </span>
                    <span className="w-28 shrink-0 truncate text-sm text-slate-600">{row.phone_zalo}</span>
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-500">
                      {previewMessage(row.message)}
                    </span>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${statusTone(row.status)}`}>
                      {statusLabel(row.status)}
                    </span>
                  </button>
                  {open ? (
                    <div className="space-y-3 bg-slate-50 px-4 py-3 text-sm">
                      <div className="grid gap-2 sm:grid-cols-2">
                        <p>
                          <span className="text-slate-500">SĐT / Zalo: </span>
                          {zalo ? (
                            <a className="font-medium text-brand-700 hover:underline" href={zalo} target="_blank" rel="noreferrer">
                              {row.phone_zalo}
                            </a>
                          ) : (
                            row.phone_zalo
                          )}
                        </p>
                        <p>
                          <span className="text-slate-500">Email: </span>
                          {row.email ? (
                            <a className="font-medium text-brand-700 hover:underline" href={`mailto:${row.email}`}>
                              {row.email}
                            </a>
                          ) : (
                            "—"
                          )}
                        </p>
                      </div>
                      <p className="whitespace-pre-wrap text-slate-700">{row.message || "Không có ghi chú."}</p>
                      <div className="flex flex-wrap items-center gap-2">
                        <select
                          className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
                          value={row.status}
                          disabled={busyId === row.id}
                          onChange={(e) => void setStatus(row.id, e.target.value as TrainerLeadStatus)}
                        >
                          {STATUSES.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      <label className="block">
                        <span className="text-xs text-slate-500">Ghi chú nội bộ</span>
                        <textarea
                          className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                          rows={2}
                          value={noteDraft}
                          onChange={(e) => setNoteDraft(e.target.value)}
                        />
                      </label>
                      <button
                        type="button"
                        disabled={busyId === row.id}
                        className="rounded-lg bg-brand-500 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40"
                        onClick={() => void saveNote(row.id)}
                      >
                        Lưu ghi chú
                      </button>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-sm text-slate-500">
        <span>
          {total} đăng ký · trang {page}/{pages}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-3 py-1 disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Trước
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-3 py-1 disabled:opacity-40"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Sau
          </button>
        </div>
      </div>
    </div>
  );
}
