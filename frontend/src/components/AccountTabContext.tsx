"use client";

import { createContext, useContext } from "react";
import type { AuthUser } from "@/lib/auth";
import type { AccountTabId } from "@/lib/accountWorkspace";

export type AccountTabContextValue = {
  tab: AccountTabId;
  setTab: (tab: AccountTabId) => void;
  user: AuthUser;
};

const AccountTabContext = createContext<AccountTabContextValue | null>(null);

export const AccountTabProvider = AccountTabContext.Provider;

export function useAccountTab() {
  return useContext(AccountTabContext);
}
