"use client";

import { useEffect, useState } from "react";
import LegalDocument from "@/components/LegalDocument";
import {
  fetchLegalDocument,
  isLegalDocument,
  type LegalDocumentBody,
  type LegalSlug,
} from "@/lib/legalDocuments";

export default function StoredLegalDocument({
  slug,
  title,
  fallback,
  sectionIdPrefix,
  compact = false,
  heading = true,
}: {
  slug: LegalSlug;
  title: string;
  fallback: LegalDocumentBody;
  sectionIdPrefix: string;
  compact?: boolean;
  heading?: boolean;
}) {
  const [doc, setDoc] = useState(fallback);

  useEffect(() => {
    let cancelled = false;
    fetchLegalDocument(slug)
      .then((data) => {
        if (cancelled || data.source !== "saved" || !isLegalDocument(data.document)) return;
        setDoc(data.document);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [slug]);

  return (
    <LegalDocument
      title={title}
      updatedLabel={doc.updated_label}
      intro={doc.intro || undefined}
      agreement={doc.agreement || undefined}
      sections={doc.sections.map((section) => ({
        id: section.id,
        title: section.title,
        paragraphs: section.paragraphs,
        bullets: section.bullets.length > 0 ? section.bullets : undefined,
      }))}
      sectionIdPrefix={sectionIdPrefix}
      compact={compact}
      heading={heading}
    />
  );
}
