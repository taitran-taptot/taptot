export function macroSplit(protein_g: number, carbs_g: number, fat_g: number) {
  const p = (protein_g || 0) * 4;
  const c = (carbs_g || 0) * 4;
  const f = (fat_g || 0) * 9;
  const t = p + c + f || 1;
  return {
    p: (p / t) * 100,
    c: (c / t) * 100,
    f: (f / t) * 100,
    pPct: Math.round((p / t) * 100),
    cPct: Math.round((c / t) * 100),
    fPct: Math.round((f / t) * 100),
  };
}

export default function MacroBar({
  protein_g,
  carbs_g,
  fat_g,
  height = "h-2",
}: {
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  height?: string;
}) {
  const s = macroSplit(protein_g, carbs_g, fat_g);
  return (
    <div className={`macro-track ${height}`}>
      <div style={{ width: `${s.p}%` }} className="bg-brand-500" title="Đạm" />
      <div style={{ width: `${s.c}%` }} className="bg-accent-500" title="Tinh bột" />
      <div style={{ width: `${s.f}%` }} className="bg-rose-400" title="Chất béo" />
    </div>
  );
}
