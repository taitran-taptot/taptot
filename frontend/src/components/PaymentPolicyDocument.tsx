import LegalDocument from "@/components/LegalDocument";
import {
  PAYMENT_POLICY_INTRO,
  PAYMENT_POLICY_SECTIONS,
  PAYMENT_POLICY_TITLE,
  PAYMENT_POLICY_UPDATED_LABEL,
} from "@/lib/paymentPolicy";

export default function PaymentPolicyDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <LegalDocument
      title={PAYMENT_POLICY_TITLE}
      updatedLabel={PAYMENT_POLICY_UPDATED_LABEL}
      intro={PAYMENT_POLICY_INTRO}
      sections={PAYMENT_POLICY_SECTIONS}
      sectionIdPrefix="thanh-toan"
      compact={compact}
      heading={heading}
    />
  );
}
