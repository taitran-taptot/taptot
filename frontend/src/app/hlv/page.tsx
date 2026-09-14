import type { Metadata } from "next";
import TrainerAssignPanel from "@/components/TrainerAssignPanel";

export const metadata: Metadata = {
  title: "HLV — Giao lịch",
};

export default function TrainerPage() {
  return <TrainerAssignPanel />;
}
