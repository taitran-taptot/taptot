"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import { redeemCodeApi, shopApi, type RedeemBatch, type RedeemCodeRow } from "@/lib/shopApi";
import type { ShopProduct } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  unused: "Chưa dùng",
  redeemed: "Đã dùng",
  void: "Đã hủy",
};

export default function CatalogRedeemCodeAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [batches, setBatches] = useState<RedeemBatch[]>([]);
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [codes, setCodes] = useState<RedeemCodeRow[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [productId, setProductId] = useState<string>("");
  const [qty, setQty] = useState(10);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [batchPage, setBatchPage] = useState(1);
  const [batchPages, setBatchPages] = useState(1);
  const [codePage, setCodePage] = useState(1);
  const [codePages, setCodePages] = useState(1);
  const [codeTotal, setCodeTotal] = useState(0);

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== "admin") {
      router.replace("/tai-khoan");
      return;
    }
    setAllowed(true);
  }, [router]);

  const loadBatches = useCallback(async () => {
    const d = await redeemCodeApi.adminListBatches(batchPage);
    setBatches(d.items || []);
    setBatchPages(d.pages || 1);
  }, [batchPage]);

  const loadCodes = useCallback(async () => {
    if (!selectedBatch) {
      setCodes([]);
      return;
    }
    const d = await redeemCodeApi.adminListCodes({
      page: codePage,
      batch_id: selectedBatch,
      status: statusFilter || undefined,
    });
    setCodes(d.items || []);
    setCodePages(d.pages || 1);
    setCodeTotal(d.total || 0);
  }, [selectedBatch, codePage, statusFilter]);

  useEffect(() => {
    if (!allowed) return;
    setLoading(true);
    setError("");
    Promise.all([loadBatches(), shopApi.adminListProducts({ page: 1 })])
      .then(([, productsRes]) => {
        setProducts(productsRes.items || []);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [allowed, loadBatches]);

  useEffect(() => {
    if (!allowed || !selectedBatch) return;
    void loadCodes().catch((e) => setError((e as Error).message));
  }, [allowed, selectedBatch, loadCodes]);

  async function createBatch(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const created = await redeemCodeApi.adminCreateBatch({
        product_id: productId ? Number(productId) : null,
        qty,
        note: note.trim() || null,
      });
      setNote("");
      setSelectedBatch(created.id);
      setCodePage(1);
      await loadBatches();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function printBatch(id: number) {
    setError("");
    try {
      const html = await redeemCodeApi.adminPrintHtml(id);
      const w = window.open("", "_blank");
      if (!w) {
        setError("Trình duyệt chặn cửa sổ in. Cho phép popup rồi thử lại.");
        return;
      }
      w.document.write(html);
      w.document.close();
      w.focus();
      w.print();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function voidCode(id: number) {
    if (!window.confirm("Hủy mã này? Tem đã in sẽ không dùng được.")) return;
    setError("");
    try {
      await redeemCodeApi.adminVoid(id);
      await loadCodes();
      await loadBatches();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (!allowed) return null;

  return (
    <div>
      <h1 className="text-2xl font-extrabold tracking-tight">Mã trên tem</h1>
      <p className="mt-1 text-sm text-slate-500">
        Tạo lô mã, in tem (QR + chữ) dán lên sản phẩm. Mỗi mã dùng 1 lần khi khách tạo lịch.
      </p>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <div className="mt-6 grid gap-8 lg:grid-cols-2">
        <div>
          <form onSubmit={(e) => void createBatch(e)} className="space-y-3 rounded-xl border border-slate-200 p-4">
            <h2 className="font-medium text-slate-800">Tạo lô mới</h2>
            <label className="block text-sm">
              Sản phẩm
              <select
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
              >
                <option value="">Không gắn sản phẩm</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name_vi}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Số lượng (1–200)
              <input
                required
                type="number"
                min={1}
                max={200}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={qty}
                onChange={(e) => setQty(Number(e.target.value) || 1)}
              />
            </label>
            <label className="block text-sm">
              Ghi chú lô
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                placeholder="Lô dây kháng lực T9"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving ? "Đang tạo…" : "Tạo lô"}
            </button>
          </form>

          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
            {loading ? (
              <p className="p-6 text-sm text-slate-400">Đang tải…</p>
            ) : (
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Lô</th>
                    <th className="px-3 py-2">Sản phẩm</th>
                    <th className="px-3 py-2">Còn / Tổng</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.map((row) => (
                    <tr
                      key={row.id}
                      className={`cursor-pointer border-t border-slate-100 hover:bg-brand-50 ${
                        selectedBatch === row.id ? "bg-brand-50" : ""
                      }`}
                      onClick={() => {
                        setSelectedBatch(row.id);
                        setCodePage(1);
                      }}
                    >
                      <td className="px-3 py-2 font-medium">#{row.id}</td>
                      <td className="px-3 py-2">{row.product_name_vi || row.note || "—"}</td>
                      <td className="px-3 py-2">
                        {row.unused_count ?? "—"} / {row.qty}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="flex items-center justify-between border-t border-slate-100 px-3 py-2 text-xs text-slate-500">
              <span>
                trang {batchPage}/{batchPages}
              </span>
              <span className="flex gap-2">
                <button type="button" disabled={batchPage <= 1} onClick={() => setBatchPage((p) => p - 1)}>
                  Trước
                </button>
                <button type="button" disabled={batchPage >= batchPages} onClick={() => setBatchPage((p) => p + 1)}>
                  Sau
                </button>
              </span>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 p-4">
          {!selectedBatch ? (
            <p className="text-sm text-slate-500">Chọn một lô bên trái để xem mã và in tem.</p>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-medium text-slate-800">Mã lô #{selectedBatch}</h2>
                <button
                  type="button"
                  className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white"
                  onClick={() => void printBatch(selectedBatch)}
                >
                  In tem lô này
                </button>
              </div>
              <div className="mt-3 flex gap-2">
                {["", "unused", "redeemed", "void"].map((s) => (
                  <button
                    key={s || "all"}
                    type="button"
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                      statusFilter === s ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
                    }`}
                    onClick={() => {
                      setStatusFilter(s);
                      setCodePage(1);
                    }}
                  >
                    {s ? STATUS_LABEL[s] : "Tất cả"}
                  </button>
                ))}
              </div>
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="text-slate-500">
                    <tr>
                      <th className="px-2 py-2">Mã</th>
                      <th className="px-2 py-2">Trạng thái</th>
                      <th className="px-2 py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {codes.map((row) => (
                      <tr key={row.id} className="border-t border-slate-100">
                        <td className="px-2 py-2 font-mono font-semibold">{row.code}</td>
                        <td className="px-2 py-2">{STATUS_LABEL[row.status] || row.status}</td>
                        <td className="px-2 py-2 text-right">
                          {row.share_url_path ? (
                            <a className="text-brand-600 hover:underline" href={row.share_url_path}>
                              Lịch
                            </a>
                          ) : null}
                          {row.status === "unused" ? (
                            <button
                              type="button"
                              className="ml-2 text-xs text-rose-600 hover:underline"
                              onClick={() => void voidCode(row.id)}
                            >
                              Hủy
                            </button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                <span>
                  {codeTotal} mã · trang {codePage}/{codePages}
                </span>
                <span className="flex gap-2">
                  <button type="button" disabled={codePage <= 1} onClick={() => setCodePage((p) => p - 1)}>
                    Trước
                  </button>
                  <button type="button" disabled={codePage >= codePages} onClick={() => setCodePage((p) => p + 1)}>
                    Sau
                  </button>
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
