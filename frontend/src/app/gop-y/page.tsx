import FeedbackForm from "@/components/FeedbackForm";

export const metadata = { title: "Góp ý — TAPTOT" };

export default function FeedbackPage() {
  return (
    <section className="mx-auto w-full lg:max-w-4xl">
      <FeedbackForm />
    </section>
  );
}
