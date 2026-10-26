import LegalDocument from "@/components/LegalDocument";
import {
  OPERATOR_INTRO,
  OPERATOR_SECTIONS,
  OPERATOR_TITLE,
  OPERATOR_UPDATED_LABEL,
} from "@/lib/operatorInfo";

export default function OperatorDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <LegalDocument
      title={OPERATOR_TITLE}
      updatedLabel={OPERATOR_UPDATED_LABEL}
      intro={OPERATOR_INTRO}
      sections={OPERATOR_SECTIONS}
      sectionIdPrefix="don-vi"
      compact={compact}
      heading={heading}
    />
  );
}
