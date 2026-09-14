import ForgotPasswordForm from "@/components/ForgotPasswordForm";

export const metadata = { title: "Quên mật khẩu — TAPTOT" };

export default function ForgotPasswordPage() {
  return (
    <section className="py-6">
      <ForgotPasswordForm />
    </section>
  );
}
