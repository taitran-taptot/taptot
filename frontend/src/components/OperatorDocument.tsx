import StoredLegalDocument from "@/components/StoredLegalDocument";
import { LEGAL_DEFAULTS } from "@/lib/legalDocuments";
import { OPERATOR_TITLE } from "@/lib/operatorInfo";

export default function OperatorDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <StoredLegalDocument
      slug="thong-tin-don-vi"
      title={OPERATOR_TITLE}
      fallback={LEGAL_DEFAULTS["thong-tin-don-vi"]}
      sectionIdPrefix="don-vi"
      compact={compact}
      heading={heading}
    />
  );
}
