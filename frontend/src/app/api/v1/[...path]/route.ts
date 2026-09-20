import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const BACKEND =
  process.env.API_PROXY_TARGET?.replace(/\/$/, "") || "http://127.0.0.1:8000";

async function proxy(req: NextRequest, path: string[]) {
  const search = req.nextUrl.search;
  const url = `${BACKEND}/api/v1/${path.join("/")}${search}`;
  const headers = new Headers();
  const accept = req.headers.get("accept");
  const contentType = req.headers.get("content-type");
  const auth = req.headers.get("authorization");
  if (accept) headers.set("accept", accept);
  if (contentType) headers.set("content-type", contentType);
  if (auth) headers.set("authorization", auth);

  const init: RequestInit = {
    method: req.method,
    headers,
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    return Response.json(
      { detail: "Không kết nối được API. Kiểm tra backend đang chạy (cổng 8000) rồi thử lại." },
      { status: 502 },
    );
  }
  const out = new Headers();
  const resType = res.headers.get("content-type");
  if (resType) out.set("content-type", resType);
  const cacheControl = res.headers.get("cache-control");
  if (cacheControl) out.set("cache-control", cacheControl);
  const accel = res.headers.get("x-accel-buffering");
  if (accel) out.set("x-accel-buffering", accel);

  const streaming =
    Boolean(res.body) &&
    Boolean(resType && (resType.includes("text/event-stream") || resType.includes("text/plain")));
  if (streaming) {
    if (!out.has("cache-control")) out.set("cache-control", "no-cache, no-transform");
    out.set("x-accel-buffering", "no");
    return new Response(res.body, { status: res.status, headers: out });
  }

  const body = await res.arrayBuffer();
  return new Response(body, { status: res.status, headers: out });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function PUT(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
