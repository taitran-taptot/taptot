import LegalDocument from "@/components/LegalDocument";
import {
  SALES_POLICY_INTRO,
  SALES_POLICY_SECTIONS,
  SALES_POLICY_TITLE,
  SALES_POLICY_UPDATED_LABEL,
} from "@/lib/salesPolicy";

export default function SalesPolicyDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <LegalDocument
      title={SALES_POLICY_TITLE}
      updatedLabel={SALES_POLICY_UPDATED_LABEL}
      intro={SALES_POLICY_INTRO}
      sections={SALES_POLICY_SECTIONS}
      sectionIdPrefix="ban-hang"
      compact={compact}
      heading={heading}
    />
  );
}
