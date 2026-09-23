"use client";

import type { PlanInsights } from "@/lib/plansApi";
import { knowledgeHref, type PhaseKnowledgeRef } from "@/lib/phaseKnowledge";
import { softenPlanCopy } from "@/lib/planLabels";

type KnowledgeRef = PhaseKnowledgeRef;

const BLOCKS: {
  key: keyof PlanInsights["overview"];
  label: string;
  refs: KnowledgeRef[];
}[] = [
  {
    key: "mission_vi",
    label: "Bạn đang làm gì",
    refs: [],
  },
  {
    key: "outcome_vi",
    label: "Tập xong sẽ được gì",
    refs: [],
  },
  {
    key: "summary_vi",
    label: "Tổng quan",
    refs: [],
  },
  {
    key: "schedule_vi",
    label: "Lịch tập & phục hồi",
    refs: [
      { slug: "17-volume-intensity-frequency", label: "1.7 — Khối lượng, cường độ & tần suất" },
      { slug: "18-phc-hi-v-gic-ng", label: "1.8 — Phục hồi & giấc ngủ" },
      { slug: "19-progressive-overload-c-bn", label: "1.9 — Tăng dần tải" },
    ],
  },
  {
    key: "nutrition_vi",
    label: "Dinh dưỡng & calo",
    refs: [
      { slug: "12-calories-thng-d-thm-ht-cn-bng", label: "1.2 — Calo: thặng dư, thiếu hụt & cân bằng" },
      { slug: "14-macronutrients-protein-carb-fat", label: "1.4 — Đạm · tinh bột · béo" },
    ],
  },
  {
    key: "periodization_vi",
    label: "Tiến triển theo tuần",
    refs: [
      { slug: "23-deload-ng-thi-im", label: "2.3 — Deload đúng thời điểm" },
      { slug: "19-progressive-overload-c-bn", label: "1.9 — Tăng dần tải" },
    ],
  },
];

export { knowledgeHref };

export default function PlanInsightsPanel({
  insights,
  hideSummary = false,
  hideAdvice = false,
}: {
  insights: PlanInsights;
  hideSummary?: boolean;
  hideAdvice?: boolean;
}) {
  const overview = insights.overview || {};
  const advice = insights.advice_vi || [];

  const blocks = hideSummary
    ? BLOCKS.filter(({ key }) => key !== "summary_vi")
    : BLOCKS;

  return (
    <div className="space-y-3 rounded-2xl border border-sky-100 bg-sky-50/80 p-4 shadow-soft">
      <p className="text-sm font-bold text-sky-900">Kiến thức về lịch này</p>

      <div className="space-y-2">
        {blocks.map(({ key, label, refs }) => {
          const text = overview[key];
          if (!text?.trim()) return null;
          return (
            <div key={key} className="rounded-xl bg-white/90 px-3 py-2.5">
              <p className="type-kicker text-sky-800/80">{label}</p>
              <p className="mt-1 text-sm leading-relaxed text-slate-700">
                {softenPlanCopy(text)}
              </p>
              {refs.length > 0 && (
                <ul className="mt-2 space-y-1 border-t border-sky-50 pt-2">
                  <li className="text-[11px] font-semibold text-sky-800/70">Tham khảo:</li>
                  {refs.map((ref) => (
                    <li key={ref.slug}>
                      <a
                        href={knowledgeHref(ref.slug)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium text-sky-700 underline decoration-sky-200 underline-offset-2 hover:text-sky-900"
                      >
                        {ref.label}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      {!hideAdvice && advice.length > 0 && (
        <div className="rounded-xl bg-white/90 px-3 py-2.5">
          <p className="type-kicker text-sky-800/80">Lời khuyên</p>
          <ul className="mt-1.5 space-y-1">
            {advice.map((tip) => (
              <li key={tip} className="flex gap-2 text-sm text-slate-700">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-500" />
                <span>{softenPlanCopy(tip)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-[11px] text-sky-800/70">
        Gợi ý tập & dinh dưỡng chung — không thay tư vấn y tế chuyên môn.
      </p>
    </div>
  );
}
