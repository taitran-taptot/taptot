import LegalDocument from "@/components/LegalDocument";
import {
  PRIVACY_INTRO,
  PRIVACY_SECTIONS,
  PRIVACY_TITLE,
  PRIVACY_UPDATED_LABEL,
} from "@/lib/privacy";

export default function PrivacyDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <LegalDocument
      title={PRIVACY_TITLE}
      updatedLabel={PRIVACY_UPDATED_LABEL}
      intro={PRIVACY_INTRO}
      sections={PRIVACY_SECTIONS}
      sectionIdPrefix="bao-mat"
      compact={compact}
      heading={heading}
    />
  );
}
