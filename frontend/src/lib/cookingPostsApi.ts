import { apiFetch } from "./http";
import type { CookingPost, Paginated } from "./types";

export type CookingPostPayload = {
  title_vi: string;
  content_md: string;
  excerpt?: string | null;
  cover_image_url?: string | null;
  slug?: string | null;
  is_published?: boolean;
  sort_order?: number;
};

const auth = { auth: true as const };

export const cookingPostsApi = {
  listPublic: (page = 1, pageSize = 20) =>
    apiFetch<Paginated<CookingPost>>(
      `/cooking-posts?page=${page}&page_size=${pageSize}`,
    ),
  getBySlug: (slug: string) =>
    apiFetch<CookingPost>(`/cooking-posts/${encodeURIComponent(slug)}`),
  adminList: (p: { page?: number; page_size?: number; q?: string; is_published?: string } = {}) => {
    const u = new URLSearchParams();
    if (p.page) u.set("page", String(p.page));
    if (p.page_size) u.set("page_size", String(p.page_size));
    if (p.q) u.set("q", p.q);
    if (p.is_published) u.set("is_published", p.is_published);
    const qs = u.toString();
    return apiFetch<Paginated<CookingPost>>(`/admin/cooking-posts${qs ? `?${qs}` : ""}`, {}, auth);
  },
  adminCreate: (body: CookingPostPayload) =>
    apiFetch<CookingPost>("/admin/cooking-posts", { method: "POST", body: JSON.stringify(body) }, auth),
  adminUpdate: (id: number, body: Partial<CookingPostPayload>) =>
    apiFetch<CookingPost>(
      `/admin/cooking-posts/${id}`,
      { method: "PATCH", body: JSON.stringify(body) },
      auth,
    ),
};
