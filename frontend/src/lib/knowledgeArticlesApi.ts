import { apiFetch } from "./http";
import type { KnowledgeArticle, Paginated } from "./types";

export type KnowledgeArticleUpdate = {
  title_vi: string;
  content_md: string;
  level: string;
  read_time_min: number | null;
  sort_order: number;
  seo_title: string;
  seo_description: string;
  is_published: boolean;
};

const auth = { auth: true as const };

export const knowledgeArticlesApi = {
  adminList: () =>
    apiFetch<Paginated<KnowledgeArticle>>("/knowledge-articles?page_size=100", {}, auth),
  get: (id: number) => apiFetch<KnowledgeArticle>(`/knowledge-articles/${id}`, {}, auth),
  update: (id: number, body: KnowledgeArticleUpdate) =>
    apiFetch<KnowledgeArticle>(
      `/knowledge-articles/${id}`,
      { method: "PATCH", body: JSON.stringify(body) },
      auth,
    ),
};
