"use client";

import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { getStoredUser, isAdmin } from "@/lib/auth";
import {
  accountShellHref,
  accountShellPath,
  isAccountShellPath,
  parseAccountTab,
  type AccountTabId,
} from "@/lib/accountWorkspace";
import { useAccountTab } from "./AccountTabContext";
import AdminStatsDashboard from "./AdminStatsDashboard";
import CatalogCookingAdmin from "./CatalogCookingAdmin";
import CatalogEquipmentAdmin from "./CatalogEquipmentAdmin";
import CatalogExerciseAdmin from "./CatalogExerciseAdmin";
import CatalogFoodAdmin from "./CatalogFoodAdmin";
import CatalogShopOrderAdmin from "./CatalogShopOrderAdmin";
import CatalogShopProductAdmin from "./CatalogShopProductAdmin";
import ChangePasswordForm from "./ChangePasswordForm";
import CreateHlvForm from "./CreateHlvForm";
import MyPlansPanel from "./MyPlansPanel";

function panelForTab(tab: AccountTabId) {
  switch (tab) {
    case "ke-hoach":
      return <MyPlansPanel />;
    case "doi-mat-khau":
      return <ChangePasswordForm />;
    case "tao-hlv":
      return <CreateHlvForm />;
    case "thong-ke":
      return <AdminStatsDashboard />;
    case "bai-tap":
      return <CatalogExerciseAdmin />;
    case "dung-cu":
      return <CatalogEquipmentAdmin />;
    case "thuc-an":
      return <CatalogFoodAdmin />;
    case "bai-viet":
      return <CatalogCookingAdmin />;
    case "san-pham":
      return <CatalogShopProductAdmin />;
    case "don-hang":
      return <CatalogShopOrderAdmin />;
    default:
      return <MyPlansPanel />;
  }
}

export default function AccountWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const ctx = useAccountTab();
  const user = ctx?.user ?? getStoredUser();
  const role = user?.role;
  const rawTab = search.get("tab");
  const tab = ctx?.tab ?? parseAccountTab(rawTab, role);

  useEffect(() => {
    if (!user) return;
    const path = pathname.replace(/\/$/, "") || "/";
    if (isAdmin(role) && path === "/tai-khoan") {
      router.replace(accountShellHref(role, rawTab));
      return;
    }
    if (!isAdmin(role) && path === "/tai-khoan/quan-tri") {
      router.replace(accountShellHref(role, rawTab));
    }
  }, [pathname, rawTab, role, router, user]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [tab]);

  if (!user) {
    return <p className="py-10 text-center text-sm text-slate-400">Đang tải…</p>;
  }

  return <div className="min-w-0">{panelForTab(tab)}</div>;
}
