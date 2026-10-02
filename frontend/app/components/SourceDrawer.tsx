"use client";

import { useEffect, useState } from "react";
import type { Source } from "./types";
import { CATALOG_SOURCE_LABEL, cleanTitle, humanizeSection, pageLabel } from "./utils";

interface SourceDrawerProps {
  source: Source | null;
  onClose: () => void;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p
        style={{
          fontSize: "10px",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          color: "var(--text-secondary)",
          fontWeight: 600,
          marginBottom: "4px",
        }}
      >
        {label}
      </p>
      <div style={{ fontSize: "13px", color: "var(--text-primary)" }}>{children}</div>
    </div>
  );
}

export default function SourceDrawer({ source, onClose }: SourceDrawerProps) {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    if (!source) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [source, onClose]);

  if (!source) return null;

  const page = pageLabel(source);
  const section = humanizeSection(source.section);

  const panelStyle: React.CSSProperties = isMobile
    ? {
        left: 0,
        right: 0,
        bottom: 0,
        top: "auto",
        width: "100%",
        maxHeight: "75vh",
        borderTop: "1px solid var(--border)",
        borderRadius: "14px 14px 0 0",
        animation: "sourceSlideUp 200ms ease both",
      }
    : {
        right: 0,
        top: 0,
        bottom: 0,
        width: "360px",
        maxWidth: "100vw",
        borderLeft: "1px solid var(--border)",
        animation: "sourceSlideIn 200ms ease both",
      };

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        style={{ background: "rgba(0,0,0,0.35)" }}
        onClick={onClose}
        aria-hidden
      />

      <div
        className="fixed z-50 flex flex-col"
        style={{
          ...panelStyle,
          background: "var(--surface)",
          boxShadow: "var(--shadow-md)",
        }}
        role="dialog"
        aria-modal="true"
        aria-label="Source details"
      >
        <style>{`
          @keyframes sourceSlideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
          @keyframes sourceSlideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
        `}</style>

        {/* Header */}
        <div
          className="flex items-center gap-2 shrink-0"
          style={{ padding: "0 12px", height: "48px", borderBottom: "1px solid var(--border)" }}
        >
          <button
            type="button"
            onClick={onClose}
            className="flex items-center justify-center shrink-0"
            style={{ width: "26px", height: "26px", borderRadius: "6px", color: "var(--text-secondary)", cursor: "pointer" }}
            aria-label="Back"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
          </button>

          <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>
            Source Details
          </span>

          <div className="flex-1" />

          <button
            type="button"
            onClick={onClose}
            className="flex items-center justify-center shrink-0"
            style={{ width: "26px", height: "26px", borderRadius: "6px", color: "var(--text-secondary)", cursor: "pointer" }}
            aria-label="Close source details"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <h2 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.35 }}>
              {cleanTitle(source)}
            </h2>
            <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "4px" }}>
              {CATALOG_SOURCE_LABEL}
            </p>
          </div>

          {section && <Field label="Section">{section}</Field>}

          {page && <Field label="Page">{page}</Field>}

          <Field label="Excerpt">
            <div
              style={{
                background: "var(--surface-elevated)",
                borderLeft: "2px solid var(--maroon)",
                borderRadius: "8px",
                padding: "12px",
                fontSize: "12px",
                lineHeight: 1.6,
                fontStyle: "italic",
                color: "var(--text-primary)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              &ldquo;{source.text}&rdquo;
            </div>
          </Field>
        </div>
      </div>
    </>
  );
}
