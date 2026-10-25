import Link from "next/link";
import { PLANK_SUCCESS_PERCENT } from "@/lib/fitness-tracker/session/discount";

const FAIL_COPY = "Hãy cố gắng rèn luyện thêm, chúng tôi sẽ tiếp tục đồng hành cùng bạn.";

export function pushupResultCopy(reps: number, percent: number): { success: boolean; message: string } {
  if (reps <= 0) return { success: false, message: FAIL_COPY };
  return {
    success: true,
    message: `Chúc mừng bạn đã hoàn thành ${reps} cái chống đẩy, bạn nhận được khuyến mãi giảm giá ${percent}% khi mua dụng cụ của TAPTOT.`,
  };
}

export function plankResultCopy(success: boolean): { success: boolean; message: string } {
  if (!success) return { success: false, message: FAIL_COPY };
  return {
    success: true,
    message: `Chúc mừng bạn đã hoàn thành 1 phút plank, bạn nhận được khuyến mãi giảm giá ${PLANK_SUCCESS_PERCENT}% khi mua dụng cụ của TAPTOT.`,
  };
}

const CONFETTI_COLORS = ["#22c55e", "#4ade80", "#86efac", "#f59e0b", "#fbbf24", "#fb923c", "#34d399"];

const CONFETTI_PIECES = Array.from({ length: 32 }, (_, i) => ({
  x: `${3 + ((i * 17) % 94)}%`,
  delay: `${(i % 10) * 0.06}s`,
  drift: `${(i % 2 === 0 ? 1 : -1) * (12 + (i % 7) * 8)}px`,
  w: `${8 + (i % 5)}px`,
  h: `${11 + (i % 6)}px`,
  color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
}));

export default function EventResultPopup({
  open,
  success,
  message,
}: {
  open: boolean;
  success: boolean;
  message: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden bg-slate-950/50 p-4">
      {success ? (
        <div className="event-confetti" aria-hidden>
          {CONFETTI_PIECES.map((piece, i) => (
            <span
              key={i}
              className="event-confetti-piece"
              style={{
                ["--x" as string]: piece.x,
                ["--delay" as string]: piece.delay,
                ["--drift" as string]: piece.drift,
                ["--w" as string]: piece.w,
                ["--h" as string]: piece.h,
                ["--c" as string]: piece.color,
              }}
            />
          ))}
        </div>
      ) : null}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="event-result-title"
        className="relative z-10 w-full max-w-md animate-in rounded-3xl bg-white p-6 text-center shadow-xl"
      >
        <h2 id="event-result-title" className="text-lg font-bold text-slate-900">
          Kết quả
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-slate-700">{message}</p>
        <div className="mt-5 grid gap-2">
          <Link
            href="/sukien"
            className={`inline-flex min-h-11 items-center justify-center rounded-xl px-4 py-3 text-center text-sm font-bold ${
              success
                ? "border border-slate-200 bg-white text-slate-800 hover:bg-slate-50"
                : "bg-brand-500 text-white hover:bg-brand-600"
            }`}
          >
            Tham gia sự kiện khác
          </Link>
          {success ? (
            <Link
              href="/mua-dung-cu?uu-dai=1"
              className="inline-flex min-h-11 items-center justify-center rounded-xl bg-brand-500 px-4 py-3 text-center text-sm font-bold text-white hover:bg-brand-600"
            >
              Mua dụng cụ với ưu đãi
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );
}
