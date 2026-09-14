import type { Metadata } from "next";
import TrainerClientsPanel from "@/components/TrainerClientsPanel";

export const metadata: Metadata = {
  title: "Quản lý khách hàng",
};

export default function TrainerClientsPage() {
  return <TrainerClientsPanel />;
}
