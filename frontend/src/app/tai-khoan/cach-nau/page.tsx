import { redirect } from "next/navigation";

type PageProps = { searchParams: Promise<{ mon?: string; slug?: string }> };

export default async function Page({ searchParams }: PageProps) {
  const sp = await searchParams;
  const mon = (sp.mon || sp.slug || "").trim();
  if (mon) {
    redirect(`/cach-nau?mon=${encodeURIComponent(mon)}`);
  }
  redirect("/cach-nau");
}
