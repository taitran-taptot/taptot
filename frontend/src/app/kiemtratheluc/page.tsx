import { Suspense } from "react";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import FitnessTestHub from "@/components/fitness-test/FitnessTestHub";

export const metadata = {
  title: `Kiểm tra thể lực${BRAND_TITLE_SUFFIX}`,
  description:
    "TAPTOT chuẩn bị các tiêu chuẩn thể lực để kiểm tra đầu vào nhằm biết người tập có phù hợp với thử thách tương ứng hay không.",
};

type PageProps = {
  searchParams: Promise<{ goi?: string; gender?: string }>;
};

export default async function KiemTraTheLucPage({ searchParams }: PageProps) {
  const query = await searchParams;
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Đang tải…</p>}>
      <FitnessTestHub presetOffer={query.goi} presetGender={query.gender} />
    </Suspense>
  );
}
