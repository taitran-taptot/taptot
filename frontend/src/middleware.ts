import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

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
  return NextResponse.next();
}

export const config = {
  matcher: ["/thuc-an", "/mon-truyen-thong"],
};
