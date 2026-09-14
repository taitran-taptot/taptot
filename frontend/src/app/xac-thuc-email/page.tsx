"use client";

import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";

function VerifyEmailInner() {
  const sp = useSearchParams();
  const router = useRouter();
  const token = sp.get("token") || "";
  const [err, setErr] = useState("");
  const [ok, setOk] = useState(false);

  useEffect(() => {
    if (!token) {
      setErr("Link không hợp lệ — thiếu token.");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        await apiFetch(
          "/auth/verify-email",
          { method: "POST", body: JSON.stringify({ token }) },
          { auth: false },
        );
        if (!cancelled) {
          setOk(true);
          setTimeout(() => router.push("/dang-nhap"), 2000);
        }
      } catch (ex) {
        if (!cancelled) setErr((ex as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, router]);

  if (!token) {
    return (
      <div className="mx-auto max-w-md rounded-2xl bg-white p-6 text-center shadow-soft">
        <p className="text-rose-600">Link xác thực email không hợp lệ.</p>
        <Link href="/dang-nhap" className="mt-4 inline-block font-semibold text-brand-600">
          Đăng nhập
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md space-y-3 rounded-2xl bg-white p-6 text-center shadow-soft">
      <h1 className="text-2xl font-extrabold">Xác thực email</h1>
      {err && <p className="text-sm text-rose-600">{err}</p>}
      {ok && <p className="text-sm text-brand-600">Email đã xác thực. Chuyển sang đăng nhập…</p>}
      {!err && !ok && <p className="text-sm text-slate-500">Đang xác thực…</p>}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <section className="py-6">
      <Suspense fallback={<p className="text-center text-slate-400">Đang tải…</p>}>
        <VerifyEmailInner />
      </Suspense>
    </section>
  );
}
