"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { aiApi } from "@/lib/authApi";
import { BRAND_NAME } from "@/lib/brand";

type Role = "assistant" | "user";

type ChatMessage = {
  id: number | string;
  role: Role;
  text: string;
};

const WELCOME =
  "Chào bạn! Mình là TAPTOT. Hỏi gì về tập luyện cũng được — không cần biết thuật ngữ.";

const QUICK_ACTIONS = [
  "Hôm nay tôi nên tập gì?",
  "Tạo lịch tập cho tôi",
  "Tôi muốn giảm 5kg",
  "Bài này tập như thế nào?",
  "Tôi nên ăn gì sau khi tập?",
];

export function useTaptotChat() {
  const nextId = useRef(1);
  const conversationId = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: 0, role: "assistant", text: WELCOME },
  ]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [pendingLabel, setPendingLabel] = useState("Đang soạn…");

  function cancelPending() {
    abortRef.current?.abort();
    abortRef.current = null;
    setPending(false);
    setPendingLabel("Đang soạn…");
  }

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    aiApi
      .chatHistory()
      .then((hist) => {
        if (cancelled) return;
        if (hist.conversation_id) conversationId.current = hist.conversation_id;
        if (!hist.messages?.length) return;
        setMessages(
          hist.messages
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((m) => ({
              id: m.id,
              role: m.role,
              text: m.content,
            })),
        );
        const maxId = hist.messages.reduce((acc, m) => Math.max(acc, Number(m.id) || 0), 0);
        nextId.current = maxId + 1;
      })
      .catch(() => {
        /* keep welcome if history fails */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function send(textOverride?: string) {
    const text = (textOverride ?? draft).trim();
    if (!text || pending) return;
    const userMsg: ChatMessage = { id: nextId.current++, role: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setDraft("");
    setPending(true);
    setPendingLabel("Đang soạn…");

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    let assembled = "";
    try {
      await aiApi.chat(
        { message: text, conversation_id: conversationId.current },
        {
          signal: ac.signal,
          onStatus: (label) => setPendingLabel(label),
          onDelta: (chunk) => {
            assembled += chunk;
            const snapshot = assembled;
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant" && String(last.id).startsWith("live-")) {
                return [...prev.slice(0, -1), { ...last, text: snapshot }];
              }
              return [...prev, { id: `live-${nextId.current}`, role: "assistant", text: snapshot }];
            });
          },
          onDone: (info) => {
            if (info.conversation_id) conversationId.current = info.conversation_id;
            if (info.message_id) {
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last?.role === "assistant" && String(last.id).startsWith("live-")) {
                  return [...prev.slice(0, -1), { ...last, id: info.message_id! }];
                }
                return prev;
              });
            }
          },
        },
      );
      if (!assembled) {
        setMessages((prev) => [
          ...prev,
          { id: nextId.current++, role: "assistant", text: "Mình chưa có câu trả lời. Thử hỏi lại nhé." },
        ]);
      }
    } catch (err) {
      if (ac.signal.aborted) return;
      const msg = err instanceof Error ? err.message : "Không gửi được tin nhắn.";
      setMessages((prev) => [...prev, { id: nextId.current++, role: "assistant", text: msg }]);
    } finally {
      if (abortRef.current === ac) abortRef.current = null;
      if (!ac.signal.aborted) {
        setPending(false);
        setPendingLabel("Đang soạn…");
      }
    }
  }

  return { messages, draft, setDraft, pending, pendingLabel, send, cancelPending };
}

export default function TaptotChatPanel({
  messages,
  draft,
  setDraft,
  pending,
  pendingLabel = "Đang soạn…",
  send,
  onClose,
  inputId = "taptot-chat-input",
}: ReturnType<typeof useTaptotChat> & { onClose?: () => void; inputId?: string }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, pending, pendingLabel]);

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  const canSend = Boolean(draft.trim()) && !pending;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl bg-white shadow-soft">
      <div className="flex shrink-0 items-start gap-3 border-b border-slate-100 px-4 py-3">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-brand-500 text-sm font-extrabold text-white">
          T
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-extrabold tracking-tight text-slate-900">Chat {BRAND_NAME}</p>
          <p className="mt-0.5 text-xs leading-snug text-slate-400">
            Hỏi TAPTOT như hỏi bạn tập cùng
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-slate-400 hover:bg-slate-50 hover:text-slate-700"
            aria-label="Đóng chat"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-3" aria-live="polite">
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <p
              className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                m.role === "user"
                  ? "rounded-br-md bg-brand-500 text-white"
                  : "rounded-bl-md bg-slate-50 text-slate-700"
              }`}
            >
              {m.text}
            </p>
          </div>
        ))}
        {pending && !messages.some((m) => String(m.id).startsWith("live-")) && (
          <div className="flex justify-start">
            <p className="rounded-2xl rounded-bl-md bg-slate-50 px-3 py-2 text-sm text-slate-400">
              {pendingLabel}
            </p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {messages.length <= 1 && !pending && (
        <div className="flex shrink-0 flex-wrap gap-1.5 border-t border-slate-50 px-3 py-2">
          {QUICK_ACTIONS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => void send(q)}
              className="rounded-full bg-brand-50 px-3 py-1.5 text-left text-xs font-semibold text-brand-800 hover:bg-brand-100"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      <form
        className="shrink-0 border-t border-slate-100 p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <label className="sr-only" htmlFor={inputId}>
          Nhắn với {BRAND_NAME}
        </label>
        <div className="flex items-end gap-2">
          <textarea
            id={inputId}
            rows={2}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Nhắn TAPTOT…"
            className="field min-h-[2.75rem] flex-1 resize-none py-2 text-sm"
          />
          <button
            type="submit"
            disabled={!canSend}
            className="rounded-xl bg-brand-500 px-3 py-2 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Gửi
          </button>
        </div>
      </form>
    </div>
  );
}
