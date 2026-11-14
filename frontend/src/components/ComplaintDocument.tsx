import StoredLegalDocument from "@/components/StoredLegalDocument";
import { LEGAL_DEFAULTS } from "@/lib/legalDocuments";
import { COMPLAINT_TITLE } from "@/lib/complaintPolicy";

export default function ComplaintDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <StoredLegalDocument
      slug="khieu-nai"
      title={COMPLAINT_TITLE}
      fallback={LEGAL_DEFAULTS["khieu-nai"]}
      sectionIdPrefix="khieu-nai"
      compact={compact}
      heading={heading}
    />
  );
}
