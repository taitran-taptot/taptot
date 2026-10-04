import { redirect } from "next/navigation";
import { cookPostHref } from "@/lib/foodRoutes";

type PageProps = { params: Promise<{ slug: string }> };

export default async function Page({ params }: PageProps) {
  const { slug } = await params;
  redirect(cookPostHref(slug));
}
