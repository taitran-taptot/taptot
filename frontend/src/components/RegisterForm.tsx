"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { authApi } from "@/lib/authApi";
import { safeNext } from "@/lib/safeNext";
import TermsConsent, { termsAccepted } from "@/components/TermsConsent";

type AccountRole = "user" | "trainer";

export default function RegisterForm() {
  const router = useRouter();
  const search = useSearchParams();
  const next = safeNext(search.get("next"));
  const [role, setRole] = useState<AccountRole>("user");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [ageOk, setAgeOk] = useState(false);
  const [termsOk, setTermsOk] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!termsAccepted(ageOk, termsOk)) {
      setErr("Hãy xác nhận độ tuổi, sức khỏe và điều khoản trước khi tạo tài khoản.");
      return;
    }
    setErr("");
    setLoading(true);
    try {
      const user = await authApi.registerAndSave(email, password, displayName, role);
      if (user.role === "trainer" || user.role === "admin") {
        router.push(next === "/tai-khoan" ? "/hlv" : next);
      } else {
        router.push(next);
      }
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-soft">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">Đăng ký</h1>
        <p className="mt-1 text-sm text-slate-500">Miễn phí — bắt đầu hành trình fitness của bạn.</p>
      </div>
      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}

      <div>
        <p className="mb-2 text-sm font-semibold text-slate-600">Bạn là</p>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setRole("user")}
            className={`rounded-xl border px-3 py-3 text-left transition ${
              role === "user"
                ? "border-brand-500 bg-brand-50 ring-2 ring-brand-200"
                : "border-slate-200 bg-white hover:border-brand-300"
            }`}
          >
            <p className="text-sm font-bold text-slate-800">Người tập</p>
            <p className="mt-0.5 text-[11px] leading-snug text-slate-500">
              Tạo lịch, theo dõi dinh dưỡng & tập luyện
            </p>
          </button>
          <button
            type="button"
            onClick={() => setRole("trainer")}
            className={`rounded-xl border px-3 py-3 text-left transition ${
              role === "trainer"
                ? "border-brand-500 bg-brand-50 ring-2 ring-brand-200"
                : "border-slate-200 bg-white hover:border-brand-300"
            }`}
          >
            <p className="text-sm font-bold text-slate-800">Huấn luyện viên</p>
            <p className="mt-0.5 text-[11px] leading-snug text-slate-500">
              Quản lý khách hàng, giao lịch & theo dõi
            </p>
          </button>
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Tên hiển thị</label>
        <input required value={displayName} onChange={(e) => setDisplayName(e.target.value)} className="field" />
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Email</label>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="field" />
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">
          Mật khẩu (≥8 ký tự, gồm chữ và số)
        </label>
        <input
          type="password"
          required
          minLength={8}
          pattern="(?=.*[A-Za-z])(?=.*\d).{8,}"
          title="Ít nhất 8 ký tự, có chữ và số"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="field"
        />
      </div>
      <TermsConsent
        idPrefix="register"
        ageOk={ageOk}
        termsOk={termsOk}
        onAgeOk={setAgeOk}
        onTermsOk={setTermsOk}
      />
      <button
        type="submit"
        disabled={loading || !termsAccepted(ageOk, termsOk)}
        className="w-full rounded-xl bg-brand-500 py-3 font-bold text-white hover:bg-brand-600 disabled:opacity-50"
      >
        {loading ? "Đang tạo…" : role === "trainer" ? "Tạo tài khoản HLV" : "Tạo tài khoản"}
      </button>
      <p className="text-center text-sm text-slate-500">
        Đã có tài khoản?{" "}
        <Link href={`/dang-nhap?next=${encodeURIComponent(next)}`} className="font-semibold text-brand-600 hover:underline">
          Đăng nhập
        </Link>
      </p>
    </form>
  );
}
