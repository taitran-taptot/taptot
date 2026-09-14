"use client";

import { useMemo, useState } from "react";
import {
  DURATION_OPTS,
  EXPERIENCE_OPTS,
  GENDER_OPTS,
  GYM_SESSION_BY_MIN,
  HOME_EQUIP_OPTS,
  HOME_SESSION_BY_MIN,
  LOCATION_OPTS,
  SESSIONS_OPTS,
  SPLIT_LEGEND,
  expandWeekDays,
  lookupWeekSplit,
  type ExperienceKey,
  type GenderKey,
  type HomeEquipKey,
  type LocationKey,
} from "@/lib/scheduleSpecMaster";

function SelectField<T extends string | number>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T;
  onChange: (v: T) => void;
  options: { key: T; label: string }[];
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-semibold text-slate-600">{label}</span>
      <select
        value={String(value)}
        onChange={(e) => {
          const raw = e.target.value;
          const matched = options.find((o) => String(o.key) === raw);
          if (matched) onChange(matched.key);
        }}
        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-800 shadow-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
      >
        {options.map((o) => (
          <option key={String(o.key)} value={String(o.key)}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function ScheduleSpecExplorer() {
  const [experience, setExperience] = useState<ExperienceKey>("0-1");
  const [gender, setGender] = useState<GenderKey>("male");
  const [location, setLocation] = useState<LocationKey>("gym");
  const [homeEquip, setHomeEquip] = useState<HomeEquipKey>("with_equip");
  const [sessions, setSessions] = useState<number>(3);
  const [duration, setDuration] = useState<number>(60);

  const weekCode = useMemo(
    () =>
      lookupWeekSplit({
        experience,
        sessions,
        gender,
        location,
        homeEquip,
      }),
    [experience, sessions, gender, location, homeEquip],
  );

  const weekDays = useMemo(() => (weekCode ? expandWeekDays(weekCode) : []), [weekCode]);

  const gymSpec = GYM_SESSION_BY_MIN[duration];
  const homeSpec = HOME_SESSION_BY_MIN[duration];

  const profileSummary = [
    EXPERIENCE_OPTS.find((o) => o.key === experience)?.label,
    GENDER_OPTS.find((o) => o.key === gender)?.label,
    LOCATION_OPTS.find((o) => o.key === location)?.label,
    location === "home" ? HOME_EQUIP_OPTS.find((o) => o.key === homeEquip)?.label : null,
    `${sessions} buổi/tuần`,
    `${duration}p/buổi`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <section className="mx-auto max-w-3xl space-y-8">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">Spec Master</p>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
          Xem lịch theo hồ sơ
        </h1>
        <p className="text-sm text-slate-500">
          Chọn dropdown theo thứ tự: kinh nghiệm → giới tính → nơi tập → (dụng cụ nếu tại nhà) → số
          buổi → thời lượng. Dữ liệu lấy từ bảng Master (Google Sheet).
        </p>
      </header>

      <div className="grid gap-4 rounded-2xl border border-slate-100 bg-white p-5 shadow-soft sm:grid-cols-2">
        <SelectField
          label="1. Kinh nghiệm tập / chơi thể thao"
          value={experience}
          onChange={setExperience}
          options={EXPERIENCE_OPTS}
        />
        <SelectField label="2. Giới tính" value={gender} onChange={setGender} options={GENDER_OPTS} />
        <SelectField
          label="3. Nơi tập"
          value={location}
          onChange={setLocation}
          options={LOCATION_OPTS}
        />
        {location === "home" ? (
          <SelectField
            label="4. Dụng cụ tại nhà"
            value={homeEquip}
            onChange={setHomeEquip}
            options={HOME_EQUIP_OPTS}
          />
        ) : (
          <div className="hidden sm:block" aria-hidden />
        )}
        <SelectField
          label={location === "home" ? "5. Số buổi / tuần" : "4. Số buổi / tuần"}
          value={sessions}
          onChange={setSessions}
          options={SESSIONS_OPTS.map((n) => ({ key: n, label: `${n} buổi` }))}
        />
        <SelectField
          label={location === "home" ? "6. Thời gian / buổi" : "5. Thời gian / buổi"}
          value={duration}
          onChange={setDuration}
          options={DURATION_OPTS.map((n) => ({ key: n, label: `${n}p` }))}
        />
      </div>

      <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
        <span className="font-semibold text-slate-800">Hồ sơ:</span> {profileSummary}
      </p>

      <div className="space-y-3 rounded-2xl border border-slate-100 bg-white p-5 shadow-soft">
        <h2 className="text-lg font-bold text-slate-900">Mẫu tuần</h2>
        {weekCode ? (
          <>
            <p className="text-2xl font-extrabold tracking-tight text-brand-600">{weekCode}</p>
            <ol className="mt-3 space-y-2">
              {weekDays.map((day, i) => (
                <li
                  key={`${day}-${i}`}
                  className="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-500 text-sm font-bold text-white">
                    {i + 1}
                  </span>
                  <span className="font-semibold text-slate-800">{day}</span>
                </li>
              ))}
            </ol>
          </>
        ) : (
          <p className="text-sm text-rose-600">Không tìm thấy mẫu tuần cho tổ hợp này.</p>
        )}
      </div>

      <div className="space-y-3 rounded-2xl border border-slate-100 bg-white p-5 shadow-soft">
        <h2 className="text-lg font-bold text-slate-900">
          Cấu trúc 1 buổi ({location === "gym" ? "Gym" : "Tại nhà"} · {duration}p)
        </h2>

        {location === "gym" && gymSpec ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <tbody className="divide-y divide-slate-100">
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Warm-up</th>
                  <td className="py-2 font-medium text-slate-800">{gymSpec.warmup}</td>
                </tr>
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Tập tạ</th>
                  <td className="py-2 font-medium text-slate-800">{gymSpec.lifting}</td>
                </tr>
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Cardio</th>
                  <td className="py-2 font-medium text-slate-800">{gymSpec.cardio}</td>
                </tr>
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Cool-down</th>
                  <td className="py-2 font-medium text-slate-800">{gymSpec.cooldown}</td>
                </tr>
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Tổng bài tạ</th>
                  <td className="py-2 font-medium text-slate-800">{gymSpec.totalLifts} bài</td>
                </tr>
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Compound</th>
                  <td className="py-2 font-medium text-slate-800">
                    {gymSpec.compounds} bài · {gymSpec.compoundSets} set · nghỉ {gymSpec.compoundRest}
                  </td>
                </tr>
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Isolate</th>
                  <td className="py-2 font-medium text-slate-800">
                    {gymSpec.isolates} bài · {gymSpec.isolateSets} set · nghỉ {gymSpec.isolateRest}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : null}

        {location === "home" && homeSpec ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <tbody className="divide-y divide-slate-100">
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Warm-up</th>
                  <td className="py-2 font-medium text-slate-800">{homeSpec.warmup}</td>
                </tr>
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Phần chính</th>
                  <td className="py-2 font-medium text-slate-800">{homeSpec.main}</td>
                </tr>
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Cool-down</th>
                  <td className="py-2 font-medium text-slate-800">{homeSpec.cooldown}</td>
                </tr>
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Kháng lực</th>
                  <td className="py-2 font-medium text-slate-800">
                    {homeSpec.resistanceCount} bài · {homeSpec.resistanceSets} set · nghỉ{" "}
                    {homeSpec.resistanceRest}
                  </td>
                </tr>
                <tr>
                  <th className="py-2 pr-4 font-semibold text-slate-500">Thể lực</th>
                  <td className="py-2 font-medium text-slate-800">
                    {homeSpec.conditioningCount} bài · {homeSpec.conditioningMinutes}p Zone 2 · nghỉ{" "}
                    {homeSpec.conditioningRest}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <details className="rounded-2xl border border-slate-100 bg-white p-5 shadow-soft">
        <summary className="cursor-pointer text-sm font-bold text-slate-800">Quy ước mã split</summary>
        <ul className="mt-3 space-y-2 text-sm text-slate-600">
          {SPLIT_LEGEND.map((row) => (
            <li key={row.code}>
              <span className="font-semibold text-slate-800">{row.code}</span> — {row.meaning}
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
