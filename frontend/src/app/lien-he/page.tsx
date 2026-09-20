import ContactTrainerForm from "@/components/ContactTrainerForm";
import FeaturedTrainerIntro from "@/components/FeaturedTrainerIntro";

export const metadata = {
  title: "Bắt đầu hành trình với HLV — TAPTOT",
  description:
    "Đăng ký tư vấn huấn luyện viên TAPTOT qua Zalo — hoặc tự tạo lịch tập và thực đơn ngay.",
};

export default function ContactPage() {
  return (
    <section className="space-y-10 py-2 sm:py-4">
      <FeaturedTrainerIntro formHref="#dang-ky-hlv" />
      <ContactTrainerForm />
    </section>
  );
}
