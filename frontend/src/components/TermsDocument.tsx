import StoredLegalDocument from "@/components/StoredLegalDocument";
import { LEGAL_DEFAULTS } from "@/lib/legalDocuments";
import { TERMS_TITLE } from "@/lib/terms";

export default function TermsDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <StoredLegalDocument
      slug="dieu-khoan"
      title={TERMS_TITLE}
      fallback={LEGAL_DEFAULTS["dieu-khoan"]}
      sectionIdPrefix="dieu-khoan"
      compact={compact}
      heading={heading}
    />
  );
}
