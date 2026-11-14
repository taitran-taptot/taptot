import StoredLegalDocument from "@/components/StoredLegalDocument";
import { LEGAL_DEFAULTS } from "@/lib/legalDocuments";
import { PRIVACY_TITLE } from "@/lib/privacy";

export default function PrivacyDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <StoredLegalDocument
      slug="chinh-sach-bao-mat"
      title={PRIVACY_TITLE}
      fallback={LEGAL_DEFAULTS["chinh-sach-bao-mat"]}
      sectionIdPrefix="bao-mat"
      compact={compact}
      heading={heading}
    />
  );
}
