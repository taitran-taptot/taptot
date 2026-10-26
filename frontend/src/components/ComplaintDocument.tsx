import LegalDocument from "@/components/LegalDocument";
import {
  COMPLAINT_INTRO,
  COMPLAINT_SECTIONS,
  COMPLAINT_TITLE,
  COMPLAINT_UPDATED_LABEL,
} from "@/lib/complaintPolicy";

export default function ComplaintDocument({
  compact = false,
  heading = true,
}: {
  compact?: boolean;
  heading?: boolean;
}) {
  return (
    <LegalDocument
      title={COMPLAINT_TITLE}
      updatedLabel={COMPLAINT_UPDATED_LABEL}
      intro={COMPLAINT_INTRO}
      sections={COMPLAINT_SECTIONS}
      sectionIdPrefix="khieu-nai"
      compact={compact}
      heading={heading}
    />
  );
}
