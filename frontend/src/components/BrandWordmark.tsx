import { BRAND_NAME, BRAND_SNOW, BRAND_T_FIRST, BRAND_T_SECOND } from "@/lib/brand";

/** Wordmark TAP + TOT: two greens on the T's; AP/OT snow on dark, ink on light. */
export default function BrandWordmark({
  className = "",
  snow = false,
}: {
  className?: string;
  snow?: boolean;
}) {
  const rest = snow ? BRAND_SNOW : undefined;
  return (
    <span className={className} aria-label={BRAND_NAME}>
      <span style={{ color: BRAND_T_FIRST }}>T</span>
      <span style={rest ? { color: rest } : undefined}>AP</span>
      <span style={{ color: BRAND_T_SECOND }}>T</span>
      <span style={rest ? { color: rest } : undefined}>OT</span>
    </span>
  );
}
