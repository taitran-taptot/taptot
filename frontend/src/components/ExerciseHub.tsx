import Link from "next/link";

const PATHS = [
  {
    id: "exercises",
    title: "Bài tập",
    desc: "Hình, cách làm, lỗi thường gặp — lọc theo nhóm cơ và độ khó, tập ở nhà hay phòng gym.",
    cta: "Vào kho bài tập",
    href: "/bai-tap",
    tone: "light" as const,
  },
  {
    id: "equipment",
    title: "Dụng cụ",
    desc: "Danh mục dụng cụ kèm ảnh và bài tập liên quan — biết dùng gì trước khi tập.",
    cta: "Vào kho dụng cụ",
    href: "/dung-cu",
    tone: "green" as const,
  },
];

export default function ExerciseHub() {
  return (
    <div className="space-y-10 pb-4">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-10 shadow-soft ring-1 ring-brand-100/60 sm:px-10 sm:py-12">
        <p className="text-sm font-semibold tracking-wide text-brand-600 uppercase">Tập luyện</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Kho bài tập
        </h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Bài tập rõ ràng và dụng cụ đi kèm — chọn một mục bên dưới để bắt đầu.
        </p>
      </header>

      <div className="grid gap-5 md:grid-cols-2">
        {PATHS.map((p) => (
          <section
            key={p.id}
            className={`flex flex-col rounded-3xl p-6 shadow-soft sm:p-7 ${
              p.tone === "green"
                ? "bg-gradient-to-br from-brand-50 to-emerald-50 ring-1 ring-brand-100"
                : "bg-white ring-1 ring-slate-100"
            }`}
          >
            <h2 className="text-xl font-extrabold tracking-tight text-slate-900">{p.title}</h2>
            <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600">{p.desc}</p>
            <Link
              href={p.href}
              className="mt-6 inline-flex w-fit items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600"
            >
              {p.cta}
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </Link>
          </section>
        ))}
      </div>
    </div>
  );
}
