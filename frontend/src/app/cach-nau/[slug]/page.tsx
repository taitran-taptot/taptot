import { redirect } from "next/navigation";
import { cookPostHref } from "@/lib/foodRoutes";

type PageProps = { params: Promise<{ slug: string }> };

/** Legacy path `/cach-nau/:slug` — prefer query URL that works under current Next routing. */
export default async function CookingDetailPage({ params }: PageProps) {
  const { slug } = await params;
  redirect(cookPostHref(slug));
}
