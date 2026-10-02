"use client";

import { useRef, useEffect, useState } from "react";
import type { StudentProfile } from "./types";

interface ChatComposerProps {
  input: string;
  loading: boolean;
  profile: StudentProfile | null;
  onChange: (value: string) => void;
  onSend: () => void;
  onFileSelect: (file: File) => void;
  onOpenUpload: () => void;
}

function PillButton({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-1.5 shrink-0"
      style={{
        background: "var(--surface-elevated)",
        border: "1px solid var(--border)",
        borderRadius: "6px",
        fontSize: "11px",
        color: "var(--text-secondary)",
        padding: "5px 10px",
        cursor: "pointer",
        whiteSpace: "nowrap",
        transition: "border-color 160ms ease, color 160ms ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "var(--maroon)";
        e.currentTarget.style.color = "var(--maroon-text)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "var(--border)";
        e.currentTarget.style.color = "var(--text-secondary)";
      }}
    >
      <span className="shrink-0" style={{ lineHeight: 0 }} aria-hidden>
        {icon}
      </span>
      {label}
    </button>
  );
}

export default function ChatComposer({
  input,
  loading,
  profile,
  onChange,
  onSend,
  onFileSelect,
  onOpenUpload,
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [focused, setFocused] = useState(false);
  const canSend = !!input.trim() && !loading;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [input]);

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSend) onSend();
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file);
      e.target.value = "";
    }
  }

  return (
    <div className="shrink-0" style={{ padding: "12px 16px 16px" }}>
      <div style={{ maxWidth: "760px", margin: "0 auto" }}>
        <div
          style={{
            background: "var(--surface)",
            border: `1px solid ${focused ? "var(--maroon)" : "var(--border)"}`,
            borderRadius: "10px",
            padding: "10px 12px",
            transition: "border-color 160ms ease",
          }}
        >
          {/* Row 1 — textarea */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKey}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="Ask about a major, course, prerequisite, or policy..."
            rows={1}
            aria-label="Message"
            className="w-full resize-none bg-transparent outline-none"
            style={{
              fontSize: "14px",
              lineHeight: 1.6,
              color: "var(--text-primary)",
              border: "none",
              maxHeight: "160px",
            }}
          />

          {/* Row 2 — actions */}
          <div className="flex items-center gap-2" style={{ marginTop: "8px" }}>
            <div className="flex items-center gap-2 min-w-0 overflow-x-auto">
              <PillButton
                label="Attach"
                onClick={() => fileRef.current?.click()}
                icon={
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                }
              />
              <PillButton
                label="Upload Transcript"
                onClick={onOpenUpload}
                icon={
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                }
              />
            </div>

            <div className="flex-1" />

            <button
              type="button"
              onClick={onSend}
              disabled={!canSend}
              className="shrink-0 flex items-center justify-center"
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "8px",
                background: canSend ? "var(--maroon)" : "var(--surface-elevated)",
                color: canSend ? "#fff" : "var(--text-secondary)",
                cursor: canSend ? "pointer" : "not-allowed",
                border: canSend ? "none" : "1px solid var(--border)",
                transition: "background 160ms ease, color 160ms ease",
              }}
              aria-label="Send message"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>

        <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleFileChange} />

        <p className="text-center" style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "8px" }}>
          {profile
            ? "Grounded in Lafayette sources · Personalized with transcript"
            : "Grounded in Lafayette academic sources · Always verify important information"}
        </p>
      </div>
    </div>
  );
}
