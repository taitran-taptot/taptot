"use client";

import { useCallback, useEffect, useState } from "react";
import {
  collaboratorApi,
  type CollaboratorAccount,
  type PromoOrder,
  type PromoOrderPage,
} from "@/lib/collaboratorApi";
import { formatVnd } from "@/lib/labels";

const STATUS: Record<string, string> = {
  awaiting_confirm: "Chờ xác nhận",
  packing: "Đang đóng gói",
  shipping: "Đang giao",
  completed: "Hoàn thành",
  cancelled: "Đã hủy",
  placed: "Chờ xác nhận",
};

function OrderList({
  page,
  full,
}: {
  page: PromoOrderPage | null;
  full: boolean;
}) {
  if (!page) return <p className="text-sm text-slate-400">Đang tải đơn…</p>;
  if (!page.items.length) return <p className="text-sm text-slate-500">Chưa có đơn dùng mã này.</p>;
  return (
    <ul className="space-y-2">
      {page.items.map((order) => (
        <OrderRow key={order.id} order={order} full={full} />
      ))}
    </ul>
  );
}

function OrderRow({ order, full }: { order: PromoOrder; full: boolean }) {
  const place = full
    ? [order.address_line, order.ward_name, order.district_name, order.province_name].filter(Boolean).join(", ")
    : [order.district_name, order.province_name].filter(Boolean).join(", ");
  return (
    <li className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-semibold text-slate-800">{order.public_code || `#${order.id}`}</p>
        <p className="text-xs text-slate-500">{STATUS[order.order_status] || order.order_status}</p>
      </div>
      <p className="mt-1 text-slate-700">
        {order.recipient_name || "—"}
        {full && order.phone ? ` · ${order.phone}` : ""}
      </p>
      {place ? <p className="text-xs text-slate-500">{place}</p> : null}
      <ul className="mt-2 space-y-0.5 text-slate-700">
        {order.items.map((item) => (
          <li key={item.id}>
            {item.name_vi} × {item.quantity} — {formatVnd(item.line_total_vnd)}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-brand-700">
        Giảm mã {order.promo_percent ?? 0}% · −{formatVnd(order.promo_discount_vnd || 0)}
        {order.discount_vnd ? ` · thử thách −${formatVnd(order.discount_vnd)}` : ""}
        {" · "}
        Thanh toán {formatVnd(order.total_vnd)}
      </p>
      {order.created_at ? (
        <p className="mt-1 text-xs text-slate-400">{new Date(order.created_at).toLocaleString("vi-VN")}</p>
      ) : null}
    </li>
  );
}

export default function AdminCollaboratorsPanel() {
  const [rows, setRows] = useState<CollaboratorAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [percent, setPercent] = useState(10);
  const [creating, setCreating] = useState(false);
  const [codingId, setCodingId] = useState<string | null>(null);
  const [codeDrafts, setCodeDrafts] = useState<Record<string, string>>({});
  const [openId, setOpenId] = useState<string | null>(null);
  const [orders, setOrders] = useState<PromoOrderPage | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editPassword, setEditPassword] = useState("");
  const [savingId, setSavingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const data = await collaboratorApi.adminList();
      setRows(data.items);
      setDrafts(Object.fromEntries(data.items.map((row) => [row.id, String(row.discount_percent)])));
    } catch (ex) {
      setError((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    collaboratorApi
      .adminList()
      .then((data) => {
        if (cancelled) return;
        setRows(data.items);
        setDrafts(Object.fromEntries(data.items.map((row) => [row.id, String(row.discount_percent)])));
        setLoading(false);
      })
      .catch((ex: unknown) => {
        if (cancelled) return;
        setError(ex instanceof Error ? ex.message : "Không tải được danh sách");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function createAccount(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError("");
    setMsg("");
    try {
      await collaboratorApi.adminCreate({
        email,
        password,
        display_name: displayName,
        discount_percent: percent,
      });
      setMsg(`Đã tạo cộng tác viên ${email}.`);
      setEmail("");
      setPassword("");
      setDisplayName("");
      setPercent(10);
      await load();
    } catch (ex) {
      setError((ex as Error).message);
    } finally {
      setCreating(false);
    }
  }

  function startEdit(row: CollaboratorAccount) {
    setEditingId(row.id);
    setEditName(row.display_name || "");
    setEditEmail(row.email || "");
    setEditPassword("");
    setDrafts({ ...drafts, [row.id]: String(row.discount_percent) });
    setError("");
  }

  async function saveAccount(row: CollaboratorAccount) {
    const next = Number(drafts[row.id]);
    if (!Number.isInteger(next) || next < 0 || next > 100) {
      setError("Mức giảm phải là số nguyên từ 0 đến 100");
      return;
    }
    const name = editName.trim();
    const nextEmail = editEmail.trim();
    if (!name || !nextEmail) {
      setError("Tên và email không được để trống");
      return;
    }
    setSavingId(row.id);
    setError("");
    try {
      await collaboratorApi.adminUpdate(row.id, {
        display_name: name,
        email: nextEmail,
        discount_percent: next,
        ...(editPassword ? { password: editPassword } : {}),
      });
      setMsg(`Đã cập nhật ${nextEmail}.`);
      setEditingId(null);
      setEditPassword("");
      await load();
    } catch (ex) {
      setError((ex as Error).message);
    } finally {
      setSavingId(null);
    }
  }

  async function removeAccount(row: CollaboratorAccount) {
    const label = row.display_name || row.email || "cộng tác viên này";
    if (!window.confirm(`Xóa ${label}? Mã giảm giá ngừng dùng. Đơn đã đặt vẫn giữ.`)) return;
    setDeletingId(row.id);
    setError("");
    try {
      await collaboratorApi.adminDelete(row.id);
      if (openId === row.id) {
        setOpenId(null);
        setOrders(null);
      }
      if (editingId === row.id) setEditingId(null);
      setMsg(`Đã xóa ${label}.`);
      await load();
    } catch (ex) {
      setError((ex as Error).message);
    } finally {
      setDeletingId(null);
    }
  }

  async function createCode(userId: string) {
    const code = (codeDrafts[userId] || "").trim();
    if (!code) {
      setError("Nhập mã giảm giá");
      return;
    }
    setCodingId(userId);
    setError("");
    try {
      const created = await collaboratorApi.adminCreateCode(userId, code);
      setMsg(`Đã lưu mã ${created.code}.`);
      setCodeDrafts((prev) => ({ ...prev, [userId]: "" }));
      await load();
    } catch (ex) {
      setError((ex as Error).message);
    } finally {
      setCodingId(null);
    }
  }

  async function toggleOrders(id: string) {
    if (openId === id) {
      setOpenId(null);
      setOrders(null);
      return;
    }
    setOpenId(id);
    setOrders(null);
    try {
      setOrders(await collaboratorApi.adminOrders(id, 1, 100));
    } catch (ex) {
      setError((ex as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={(e) => void createAccount(e)} className="space-y-3 rounded-2xl bg-white p-5 shadow-soft">
        <h1 className="type-display">Cộng tác viên</h1>
        <p className="text-sm text-slate-500">
          Tạo, sửa và xóa tài khoản cộng tác viên. Mỗi người một mã do admin nhập. Đơn đã đặt giữ mức giảm lúc thanh toán.
        </p>
        {msg && <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{msg}</p>}
        {error && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>}
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm font-semibold text-slate-600">
            Tên hiển thị
            <input required value={displayName} onChange={(e) => setDisplayName(e.target.value)} className="field mt-1" />
          </label>
          <label className="block text-sm font-semibold text-slate-600">
            Email
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="field mt-1" />
          </label>
          <label className="block text-sm font-semibold text-slate-600">
            Mật khẩu
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="field mt-1"
            />
          </label>
          <label className="block text-sm font-semibold text-slate-600">
            Mức giảm (%)
            <input
              type="number"
              min={0}
              max={100}
              required
              value={percent}
              onChange={(e) => setPercent(Number(e.target.value))}
              className="field mt-1"
            />
          </label>
        </div>
        <button
          type="submit"
          disabled={creating}
          className="rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
        >
          {creating ? "Đang tạo…" : "Tạo cộng tác viên"}
        </button>
      </form>

      <div className="rounded-2xl bg-white p-5 shadow-soft">
        {loading ? (
          <p className="text-sm text-slate-400">Đang tải…</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-slate-500">Chưa có cộng tác viên.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {rows.map((row) => (
              <li key={row.id} className="py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-900">{row.display_name || row.email}</p>
                    <p className="text-sm text-slate-500">{row.email}</p>
                    <p className="mt-1 font-mono text-sm text-brand-700">{row.code || "Chưa tạo mã"}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {row.order_count} đơn · đã giảm {formatVnd(row.discount_vnd)}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => (editingId === row.id ? setEditingId(null) : startEdit(row))}
                      className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      {editingId === row.id ? "Đóng" : "Sửa"}
                    </button>
                    {!row.code ? (
                      <form
                        className="flex items-center gap-2"
                        onSubmit={(e) => {
                          e.preventDefault();
                          void createCode(row.id);
                        }}
                      >
                        <input
                          value={codeDrafts[row.id] ?? ""}
                          onChange={(e) =>
                            setCodeDrafts({ ...codeDrafts, [row.id]: e.target.value.toUpperCase() })
                          }
                          placeholder="MAGIAMGIA"
                          maxLength={32}
                          className="field w-36 font-mono uppercase"
                          aria-label={`Mã giảm giá của ${row.display_name || row.email}`}
                        />
                        <button
                          type="submit"
                          disabled={codingId === row.id}
                          className="rounded-lg bg-brand-500 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
                        >
                          {codingId === row.id ? "Đang lưu…" : "Lưu mã"}
                        </button>
                      </form>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => void toggleOrders(row.id)}
                      className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      {openId === row.id ? "Đóng đơn" : "Xem đơn"}
                    </button>
                    <button
                      type="button"
                      disabled={deletingId === row.id}
                      onClick={() => void removeAccount(row)}
                      className="rounded-lg border border-rose-200 px-3 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                    >
                      {deletingId === row.id ? "Đang xóa…" : "Xóa"}
                    </button>
                  </div>
                </div>
                {editingId === row.id ? (
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <label className="block text-sm font-semibold text-slate-600">
                      Tên hiển thị
                      <input value={editName} onChange={(e) => setEditName(e.target.value)} className="field mt-1" />
                    </label>
                    <label className="block text-sm font-semibold text-slate-600">
                      Email
                      <input type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} className="field mt-1" />
                    </label>
                    <label className="block text-sm font-semibold text-slate-600">
                      Mật khẩu mới
                      <input
                        type="password"
                        minLength={8}
                        value={editPassword}
                        placeholder="Để trống nếu giữ mật khẩu cũ"
                        onChange={(e) => setEditPassword(e.target.value)}
                        className="field mt-1"
                      />
                    </label>
                    <label className="block text-sm font-semibold text-slate-600">
                      Mức giảm (%)
                      <input
                        type="number"
                        min={0}
                        max={100}
                        value={drafts[row.id] ?? ""}
                        onChange={(e) => setDrafts({ ...drafts, [row.id]: e.target.value })}
                        className="field mt-1"
                      />
                    </label>
                    <div className="sm:col-span-2">
                      <button
                        type="button"
                        disabled={savingId === row.id}
                        onClick={() => void saveAccount(row)}
                        className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
                      >
                        {savingId === row.id ? "Đang lưu…" : "Lưu thay đổi"}
                      </button>
                    </div>
                  </div>
                ) : null}
                {openId === row.id ? (
                  <div className="mt-3">
                    <OrderList page={orders} full />
                    {orders && orders.total > orders.items.length ? (
                      <p className="mt-2 text-xs text-slate-400">
                        Đang hiện {orders.items.length} / {orders.total} đơn.
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
