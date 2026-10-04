import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { canonicalizeKnowledgeSlug } from "@/lib/knowledgeSlugAliases";

function knowledgePath(slug: string): string {
  return `/kien-thuc/${encodeURIComponent(slug)}`;
}

/** Map English food-library query URLs onto Vietnamese paths. */
export function middleware(request: NextRequest) {
  const url = request.nextUrl;
  if (url.pathname === "/thuc-an" && url.searchParams.get("tab") === "dishes") {
    return NextResponse.redirect(new URL("/mon-truyen-thong", request.url));
  }
  if (url.pathname === "/mon-truyen-thong" && url.searchParams.has("tab")) {
    url.search = "";
    return NextResponse.redirect(url);
  }

  const match = /^\/kien-thuc\/([^/]+)\/?$/.exec(url.pathname);
  if (match?.[1]) {
    let raw = match[1];
    try {
      raw = decodeURIComponent(raw);
    } catch {
      /* keep raw */
    }
    const canon = canonicalizeKnowledgeSlug(raw);
    if (canon && canon !== raw) {
      return NextResponse.redirect(new URL(knowledgePath(canon), request.url), 308);
    }
    return NextResponse.next();
  }

  if (url.pathname === "/kien-thuc") {
    const slug = (url.searchParams.get("bai") || url.searchParams.get("slug") || "").trim();
    if (slug) {
      const canon = canonicalizeKnowledgeSlug(slug);
      return NextResponse.redirect(new URL(knowledgePath(canon), request.url));
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/thuc-an", "/mon-truyen-thong", "/kien-thuc", "/kien-thuc/:slug"],
};
