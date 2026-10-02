"use client";

import { useState, useEffect, useRef } from "react";
import type { Message, Source } from "./types";
import SourcesList from "./SourcesList";
import { formatTime } from "./utils";

interface AssistantMessageProps {
  message: Message;
  onSourceClick: (source: Source, index: number) => void;
}

/* ── Inline rendering ──────────────────────────────────────── */

const COURSE_CODE = /\b[A-Z]{2,5}\s\d{3}\b/;
const CITATION = /\[\d+\]/;
const INLINE_SPLIT = /(\*\*[^*]+\*\*|\[\d+\]|\b[A-Z]{2,5}\s\d{3}\b)/g;

function CourseCode({ children }: { children: string }) {
  return <span style={{ color: "var(--maroon-text)", fontWeight: 500 }}>{children}</span>;
}

function CitationChip({
  n,
  onClick,
}: {
  n: number;
  onClick: (index: number) => void;
}) {
  return (
    <sup>
      <button
        type="button"
        onClick={() => onClick(n - 1)}
        aria-label={`Open source ${n}`}
        style={{
          minWidth: "16px",
          height: "15px",
          background: "var(--maroon-subtle)",
          color: "var(--maroon-text)",
          fontSize: "9px",
          borderRadius: "3px",
          border: "none",
          padding: "0 3px",
          margin: "0 1px",
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          verticalAlign: "middle",
          lineHeight: 1,
        }}
      >
        {n}
      </button>
    </sup>
  );
}

/** Highlights course codes inside a plain text run. */
function withCourseCodes(text: string, keyPrefix: string): React.ReactNode[] {
  return text.split(/(\b[A-Z]{2,5}\s\d{3}\b)/g).map((part, i) =>
    COURSE_CODE.test(part) && /^[A-Z]{2,5}\s\d{3}$/.test(part) ? (
      <CourseCode key={`${keyPrefix}-c${i}`}>{part}</CourseCode>
    ) : (
      <span key={`${keyPrefix}-t${i}`}>{part}</span>
    )
  );
}

function renderInline(
  text: string,
  keyPrefix: string,
  onCitation: (index: number) => void
): React.ReactNode[] {
  return text.split(INLINE_SPLIT).filter(Boolean).map((part, i) => {
    const key = `${keyPrefix}-${i}`;

    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={key}>{withCourseCodes(part.slice(2, -2), key)}</strong>;
    }

    if (CITATION.test(part) && /^\[\d+\]$/.test(part)) {
      const n = parseInt(part.slice(1, -1), 10);
      return <CitationChip key={key} n={n} onClick={onCitation} />;
    }

    if (/^[A-Z]{2,5}\s\d{3}$/.test(part)) {
      return <CourseCode key={key}>{part}</CourseCode>;
    }

    return <span key={key}>{part}</span>;
  });
}

/* ── Block rendering ───────────────────────────────────────── */

const BULLET = /^\s*([-*•])\s+/;
const NUMBERED = /^\s*\d+[.)]\s+/;

function isListLine(line: string) {
  return BULLET.test(line) || NUMBERED.test(line);
}

function stripListMarker(line: string) {
  return line.replace(BULLET, "").replace(NUMBERED, "");
}

function looksLikeHeading(line: string) {
  const t = line.trim();
  if (!t || t.length > 70) return false;
  return !/[.!?,:;]$/.test(t);
}

function renderContent(content: string, onCitation: (index: number) => void): React.ReactNode[] {
  const lines = content.split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === "") {
      i++;
      continue;
    }

    // Markdown heading
    if (/^#{1,6}\s/.test(line)) {
      blocks.push(
        <p
          key={`h-${i}`}
          style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", marginTop: "14px" }}
        >
          {renderInline(line.replace(/^#{1,6}\s/, ""), `h-${i}`, onCitation)}
        </p>
      );
      i++;
      continue;
    }

    // List block
    if (isListLine(line)) {
      const items: string[] = [];
      while (i < lines.length && (isListLine(lines[i]) || lines[i].trim() === "")) {
        if (lines[i].trim() === "") {
          // stop unless another list line follows
          const next = lines[i + 1];
          if (!next || !isListLine(next)) break;
          i++;
          continue;
        }
        items.push(stripListMarker(lines[i]));
        i++;
      }
      blocks.push(
        <ul key={`ul-${i}`} style={{ marginTop: "6px", display: "flex", flexDirection: "column", gap: "4px" }}>
          {items.map((item, j) => (
            <li key={j} style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
              <span aria-hidden style={{ color: "var(--maroon-text)", lineHeight: 1.7, flexShrink: 0 }}>
                &bull;
              </span>
              <span style={{ minWidth: 0 }}>{renderInline(item, `li-${i}-${j}`, onCitation)}</span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Short, unpunctuated line followed by a list → section heading
    let k = i + 1;
    while (k < lines.length && lines[k].trim() === "") k++;
    if (looksLikeHeading(line) && k < lines.length && isListLine(lines[k])) {
      blocks.push(
        <p
          key={`sh-${i}`}
          style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", marginTop: "14px" }}
        >
          {renderInline(line.replace(/^\*\*|\*\*$/g, ""), `sh-${i}`, onCitation)}
        </p>
      );
      i++;
      continue;
    }

    // Paragraph
    blocks.push(
      <p key={`p-${i}`} style={{ marginTop: blocks.length ? "10px" : 0 }}>
        {renderInline(line, `p-${i}`, onCitation)}
      </p>
    );
    i++;
  }

  return blocks;
}

/* ── Action buttons ────────────────────────────────────────── */

function ActionButton({
  label,
  onClick,
  children,
  active,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="flex items-center justify-center"
      style={{
        width: "24px",
        height: "24px",
        borderRadius: "6px",
        background: "transparent",
        border: "none",
        color: active ? "var(--maroon-text)" : "var(--text-secondary)",
        cursor: "pointer",
        transition: "color 160ms ease",
      }}
      onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = "var(--text-primary)"; }}
      onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = "var(--text-secondary)"; }}
    >
      {children}
    </button>
  );
}

/* ── Component ─────────────────────────────────────────────── */

export default function AssistantMessage({ message, onSourceClick }: AssistantMessageProps) {
  const [copied, setCopied] = useState(false);
  const [vote, setVote] = useState<"up" | "down" | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  const sources = message.sources ?? [];

  function openSourceAt(index: number) {
    const source = sources[index];
    if (source) onSourceClick(source, index);
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <div className="flex items-start gap-3 animate-fade-in">
      <div
        className="shrink-0 flex items-center justify-center"
        style={{
          width: "28px",
          height: "28px",
          borderRadius: "999px",
          background: "var(--maroon)",
          color: "#fff",
          marginTop: "2px",
        }}
        aria-hidden
      >
        <span style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "14px", fontWeight: 600 }}>
          L
        </span>
      </div>

      <div className="flex-1 min-w-0">
        <div
          style={{
            fontSize: "14px",
            lineHeight: 1.7,
            color: "var(--text-primary)",
            maxWidth: "660px",
            wordBreak: "break-word",
          }}
        >
          {renderContent(message.content, openSourceAt)}
        </div>

        {sources.length > 0 && (
          <SourcesList sources={sources} onSourceClick={onSourceClick} />
        )}

        {/* Action row */}
        <div className="flex items-center gap-1" style={{ marginTop: "10px", maxWidth: "660px" }}>
          <ActionButton label={copied ? "Copied" : "Copy message"} onClick={handleCopy} active={copied}>
            {copied ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            )}
          </ActionButton>

          <ActionButton
            label="Helpful"
            active={vote === "up"}
            onClick={() => setVote((v) => (v === "up" ? null : "up"))}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <path d="M7 10v12" />
              <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" />
            </svg>
          </ActionButton>

          <ActionButton
            label="Not helpful"
            active={vote === "down"}
            onClick={() => setVote((v) => (v === "down" ? null : "down"))}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 14V2" />
              <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" />
            </svg>
          </ActionButton>

          <div className="flex-1" />

          <span style={{ fontSize: "10px", color: "var(--text-secondary)" }}>
            {formatTime(message.createdAt)}
          </span>
        </div>
      </div>
    </div>
  );
}
