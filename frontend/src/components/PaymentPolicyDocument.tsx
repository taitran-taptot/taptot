import StoredLegalDocument from "@/components/StoredLegalDocument";
import { LEGAL_DEFAULTS } from "@/lib/legalDocuments";
import { PAYMENT_POLICY_TITLE } from "@/lib/paymentPolicy";

export default function PaymentPolicyDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <StoredLegalDocument
      slug="chinh-sach-thanh-toan"
      title={PAYMENT_POLICY_TITLE}
      fallback={LEGAL_DEFAULTS["chinh-sach-thanh-toan"]}
      sectionIdPrefix="thanh-toan"
      compact={compact}
      heading={heading}
    />
  );
}
