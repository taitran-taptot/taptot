import type { Metadata } from "next";
import PublicTrainerProfileView from "@/components/PublicTrainerProfileView";

export const metadata: Metadata = {
  title: "Hồ sơ HLV — TAPTOT",
};

export default function PublicTrainerProfilePage() {
  return <PublicTrainerProfileView />;
}
