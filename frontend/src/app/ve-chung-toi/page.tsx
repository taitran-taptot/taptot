import AboutPage from "@/components/AboutPage";
import { BRAND_NAME, BRAND_TITLE_SUFFIX } from "@/lib/brand";

export const metadata = {
  title: `Về chúng tôi${BRAND_TITLE_SUFFIX}`,
  description: `${BRAND_NAME} giúp người Việt bắt đầu tập và ăn lành mạnh — lịch vừa sức, món quen, đồng hành khi bạn cần người kèm.`,
};

export default function VeChungToiPage() {
  return <AboutPage />;
}
