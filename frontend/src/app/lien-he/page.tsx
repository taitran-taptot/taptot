import ContactTrainerForm from "@/components/ContactTrainerForm";

export const metadata = {
  title: "Bắt đầu hành trình với HLV — TAPTOT",
  description:
    "Đăng ký tư vấn huấn luyện viên TAPTOT qua Zalo — hoặc tự tạo lịch tập và thực đơn ngay.",
};

export default function ContactPage() {
  return (
    <section className="py-2 sm:py-4">
      <ContactTrainerForm />
    </section>
  );
}
