import StartHub from "@/components/StartHub";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";

export const metadata = {
  title: `Bắt đầu${BRAND_TITLE_SUFFIX}`,
  description:
    "Tập với HLV chuyên nghiệp, thử thách 100 ngày với TAPTOT, hoặc tự tạo lịch tập.",
};

export default function BatDauPage() {
  return <StartHub />;
}
