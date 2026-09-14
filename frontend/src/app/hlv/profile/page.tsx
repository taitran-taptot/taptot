import type { Metadata } from "next";
import TrainerProfilePanel from "@/components/TrainerProfilePanel";

export const metadata: Metadata = {
  title: "Hồ sơ HLV",
};

export default function TrainerProfilePage() {
  return <TrainerProfilePanel />;
}
