import LegalDocument from "@/components/LegalDocument";
import {
  TERMS_AGREEMENT,
  TERMS_INTRO,
  TERMS_SECTIONS,
  TERMS_TITLE,
  TERMS_UPDATED_LABEL,
} from "@/lib/terms";

export default function TermsDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <LegalDocument
      title={TERMS_TITLE}
      updatedLabel={TERMS_UPDATED_LABEL}
      intro={TERMS_INTRO}
      agreement={TERMS_AGREEMENT}
      sections={TERMS_SECTIONS}
      sectionIdPrefix="dieu-khoan"
      compact={compact}
      heading={heading}
    />
  );
}
