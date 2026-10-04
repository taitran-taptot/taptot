"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import { accountShellHref, type AccountTabId } from "@/lib/accountWorkspace";

export default function RedirectToAccountTab({ tab }: { tab: AccountTabId }) {
  const router = useRouter();

  useEffect(() => {
    router.replace(accountShellHref(getStoredUser()?.role, tab));
  }, [router, tab]);

  return <p className="py-10 text-center text-sm text-slate-400">Đang mở…</p>;
}
