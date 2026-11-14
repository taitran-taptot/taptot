import StoredLegalDocument from "@/components/StoredLegalDocument";
import { LEGAL_DEFAULTS } from "@/lib/legalDocuments";
import { SALES_POLICY_TITLE } from "@/lib/salesPolicy";

export default function SalesPolicyDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <StoredLegalDocument
      slug="chinh-sach-ban-hang"
      title={SALES_POLICY_TITLE}
      fallback={LEGAL_DEFAULTS["chinh-sach-ban-hang"]}
      sectionIdPrefix="ban-hang"
      compact={compact}
      heading={heading}
    />
  );
}
