"use client";

import { useState, useEffect } from "react";
import type { Source } from "./types";
import { cleanTitle, sourceSubtitle } from "./utils";

interface SourcesListProps {
  sources: Source[];
  onSourceClick: (source: Source, index: number) => void;
}

function useIsNarrow() {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setNarrow(mq.matches);
    const handler = (e: MediaQueryListEvent) => setNarrow(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return narrow;
}

function SourceCard({
  source,
  index,
  onClick,
}: {
  source: Source;
  index: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-2 text-left"
      style={{
        background: "var(--surface-elevated)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "11px 14px",
        cursor: "pointer",
        transition: "border-color 160ms ease",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--maroon)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
    >
      <span
        className="shrink-0"
        style={{ width: "22px", color: "var(--maroon-text)", fontSize: "11px", fontWeight: 600 }}
        aria-hidden
      >
        [{index + 1}]
      </span>

      <span className="min-w-0 flex-1">
        <span
          className="block truncate"
          style={{ fontSize: "12px", fontWeight: 500, color: "var(--text-primary)" }}
        >
          {cleanTitle(source)}
        </span>
        <span className="block truncate" style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "2px" }}>
          {sourceSubtitle(source)}
        </span>
      </span>

      <span className="shrink-0" style={{ color: "var(--text-secondary)", lineHeight: 0 }} aria-hidden>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
          <polyline points="15 3 21 3 21 9" />
          <line x1="10" y1="14" x2="21" y2="3" />
        </svg>
      </span>
    </button>
  );
}

export default function SourcesList({ sources, onSourceClick }: SourcesListProps) {
  const narrow = useIsNarrow();
  const [expanded, setExpanded] = useState(false);

  if (!sources.length) return null;

  const list = (
    <div className="flex flex-col" style={{ gap: "6px", maxWidth: "660px" }}>
      {sources.map((source, i) => (
        <SourceCard key={i} source={source} index={i} onClick={() => onSourceClick(source, i)} />
      ))}
    </div>
  );

  if (narrow) {
    return (
      <div style={{ marginTop: "14px", maxWidth: "660px" }}>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="w-full flex items-center justify-between"
          style={{
            background: "var(--surface-elevated)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            padding: "9px 14px",
            fontSize: "12px",
            fontWeight: 600,
            color: "var(--text-primary)",
            cursor: "pointer",
          }}
        >
          <span>Sources ({sources.length})</span>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ transform: expanded ? "rotate(180deg)" : "none", transition: "transform 160ms ease" }}
            aria-hidden
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        {expanded && <div style={{ marginTop: "6px" }}>{list}</div>}
      </div>
    );
  }

  return (
    <div style={{ marginTop: "16px" }}>
      <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "8px" }}>
        Sources
      </p>
      {list}
    </div>
  );
}
