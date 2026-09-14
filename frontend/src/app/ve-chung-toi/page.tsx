import AboutPage from "@/components/AboutPage";
import { BRAND_NAME, BRAND_TITLE_SUFFIX } from "@/lib/brand";

export const metadata = {
  title: `Về chúng tôi${BRAND_TITLE_SUFFIX}`,
  description: `Sứ mệnh ${BRAND_NAME} và đội hình huấn luyện viên collab — lịch vừa sức, món Việt quen, đồng hành khi bạn cần người kèm.`,
};

export default function VeChungToiPage() {
  return <AboutPage />;
}
