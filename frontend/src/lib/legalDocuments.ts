import { apiFetch } from "@/lib/http";
import { COMPLAINT_INTRO, COMPLAINT_SECTIONS, COMPLAINT_UPDATED_LABEL } from "@/lib/complaintPolicy";
import type { LegalSection } from "@/lib/legalMeta";
import { OPERATOR_INTRO, OPERATOR_SECTIONS, OPERATOR_UPDATED_LABEL } from "@/lib/operatorInfo";
import { PAYMENT_POLICY_INTRO, PAYMENT_POLICY_SECTIONS, PAYMENT_POLICY_UPDATED_LABEL } from "@/lib/paymentPolicy";
import { PRIVACY_INTRO, PRIVACY_SECTIONS, PRIVACY_UPDATED_LABEL } from "@/lib/privacy";
import { SALES_POLICY_INTRO, SALES_POLICY_SECTIONS, SALES_POLICY_UPDATED_LABEL } from "@/lib/salesPolicy";
import {
  TERMS_AGREEMENT,
  TERMS_INTRO,
  TERMS_SECTIONS,
  TERMS_UPDATED_LABEL,
} from "@/lib/terms";

export type LegalSlug =
  | "dieu-khoan"
  | "chinh-sach-bao-mat"
  | "chinh-sach-ban-hang"
  | "chinh-sach-thanh-toan"
  | "khieu-nai"
  | "thong-tin-don-vi";

export type LegalDocumentSection = {
  id: string;
  title: string;
  paragraphs: string[];
  bullets: string[];
};

export type LegalDocumentBody = {
  updated_label: string;
  intro: string;
  agreement: string;
  sections: LegalDocumentSection[];
};

export type LegalDocumentResponse = {
  slug: string;
  source: string;
  document: unknown;
};

export const LEGAL_PAGES: { slug: LegalSlug; label: string }[] = [
  { slug: "dieu-khoan", label: "Điều khoản dịch vụ" },
  { slug: "chinh-sach-bao-mat", label: "Chính sách bảo mật" },
  { slug: "chinh-sach-ban-hang", label: "Chính sách bán hàng" },
  { slug: "chinh-sach-thanh-toan", label: "Thanh toán và hoàn tiền" },
  { slug: "khieu-nai", label: "Khiếu nại" },
  { slug: "thong-tin-don-vi", label: "Thông tin đơn vị" },
];

function sectionsOf(sections: LegalSection[]): LegalDocumentSection[] {
  return sections.map((section) => ({
    id: section.id,
    title: section.title,
    paragraphs: [...section.paragraphs],
    bullets: section.bullets ? [...section.bullets] : [],
  }));
}

function documentOf(
  updatedLabel: string,
  intro: string,
  sections: LegalSection[],
  agreement = "",
): LegalDocumentBody {
  return {
    updated_label: updatedLabel,
    intro,
    agreement,
    sections: sectionsOf(sections),
  };
}

export const LEGAL_DEFAULTS: Record<LegalSlug, LegalDocumentBody> = {
  "dieu-khoan": documentOf(TERMS_UPDATED_LABEL, TERMS_INTRO, TERMS_SECTIONS, TERMS_AGREEMENT),
  "chinh-sach-bao-mat": documentOf(PRIVACY_UPDATED_LABEL, PRIVACY_INTRO, PRIVACY_SECTIONS),
  "chinh-sach-ban-hang": documentOf(SALES_POLICY_UPDATED_LABEL, SALES_POLICY_INTRO, SALES_POLICY_SECTIONS),
  "chinh-sach-thanh-toan": documentOf(
    PAYMENT_POLICY_UPDATED_LABEL,
    PAYMENT_POLICY_INTRO,
    PAYMENT_POLICY_SECTIONS,
  ),
  "khieu-nai": documentOf(COMPLAINT_UPDATED_LABEL, COMPLAINT_INTRO, COMPLAINT_SECTIONS),
  "thong-tin-don-vi": documentOf(OPERATOR_UPDATED_LABEL, OPERATOR_INTRO, OPERATOR_SECTIONS),
};

export function cloneLegalDocument(document: LegalDocumentBody): LegalDocumentBody {
  return {
    updated_label: document.updated_label,
    intro: document.intro,
    agreement: document.agreement,
    sections: document.sections.map((section) => ({
      id: section.id,
      title: section.title,
      paragraphs: [...section.paragraphs],
      bullets: [...section.bullets],
    })),
  };
}

export function isLegalDocument(value: unknown): value is LegalDocumentBody {
  if (!value || typeof value !== "object") return false;
  const doc = value as Partial<LegalDocumentBody>;
  if (typeof doc.updated_label !== "string" || typeof doc.intro !== "string" || typeof doc.agreement !== "string") {
    return false;
  }
  if (!Array.isArray(doc.sections) || doc.sections.length === 0) return false;
  return doc.sections.every((section) => {
    if (!section || typeof section !== "object") return false;
    const row = section as Partial<LegalDocumentSection>;
    return (
      typeof row.id === "string" &&
      typeof row.title === "string" &&
      Array.isArray(row.paragraphs) &&
      row.paragraphs.every((item) => typeof item === "string") &&
      Array.isArray(row.bullets) &&
      row.bullets.every((item) => typeof item === "string")
    );
  });
}

export function fetchLegalDocument(slug: string) {
  return apiFetch<LegalDocumentResponse>(`/site/legal/${slug}`);
}

export function saveLegalDocument(slug: string, document: LegalDocumentBody) {
  return apiFetch<LegalDocumentResponse>(
    `/admin/site/legal/${slug}`,
    { method: "PUT", body: JSON.stringify(document) },
    { auth: true },
  );
}

export function resetLegalDocument(slug: string) {
  return apiFetch<LegalDocumentResponse>(`/admin/site/legal/${slug}`, { method: "DELETE" }, { auth: true });
}
