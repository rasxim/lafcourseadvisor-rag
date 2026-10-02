"use client";

import type { StudentProfile } from "./types";
import { progressPct } from "./utils";

const GREEN = "#3FA96A";

const CARD_ICON = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const IconCap = (
  <svg {...CARD_ICON}>
    <path d="M22 10 12 5 2 10l10 5 10-5Z" />
    <path d="M6 12v5c0 1 2.7 2.5 6 2.5s6-1.5 6-2.5v-5" />
  </svg>
);

const IconOpenBook = (
  <svg {...CARD_ICON}>
    <path d="M2 4h6a3 3 0 0 1 3 3v13a2.5 2.5 0 0 0-2.5-2.5H2Z" />
    <path d="M22 4h-6a3 3 0 0 0-3 3v13a2.5 2.5 0 0 1 2.5-2.5H22Z" />
  </svg>
);

const IconDoc = (
  <svg {...CARD_ICON}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
  </svg>
);

const IconCal = (
  <svg {...CARD_ICON}>
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" />
    <line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const DEFAULT_PROMPTS = [
  { label: "Major requirements", q: "What are the requirements for the Computer Science major?", icon: IconCap },
  { label: "Course information", q: "Tell me about CS 303 — what is it about and what are the prerequisites?", icon: IconOpenBook },
  { label: "Academic policies", q: "What is the Common Course of Study requirement?", icon: IconDoc },
  { label: "Plan my schedule", q: "What courses should I take to complete my degree efficiently?", icon: IconCal },
];

const PROFILE_PROMPTS = [
  { label: "Remaining requirements", q: "What requirements do I still need to complete for graduation?", icon: IconCap },
  { label: "What can I take next?", q: "What courses am I eligible to take next based on my completed courses?", icon: IconOpenBook },
  { label: "GPA impact", q: "How is my GPA calculated and what does it mean for my standing?", icon: IconDoc },
  { label: "Graduation timeline", q: "Am I on track to graduate on time? What's my progress?", icon: IconCal },
];

/* ── Degree progress donut ─────────────────────────────────── */

function ProgressDonut({ pct }: { pct: number }) {
  const size = 68;
  const stroke = 7;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }} aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--maroon)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c - dash}`}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)" }}>{pct}%</span>
      </div>
    </div>
  );
}

/* ── Component ─────────────────────────────────────────────── */

interface WelcomeStateProps {
  profile: StudentProfile | null;
  onSend: (query: string) => void;
  onOpenUpload: () => void;
}

export default function WelcomeState({ profile, onSend, onOpenUpload }: WelcomeStateProps) {
  const prompts = profile ? PROFILE_PROMPTS : DEFAULT_PROMPTS;
  const pct = profile ? progressPct(profile) : 0;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="flex flex-col items-center justify-center min-h-full px-4 py-10">
        {/* ── Hero ── */}
        <p
          className="text-center"
          style={{
            textTransform: "uppercase",
            letterSpacing: "0.22em",
            fontSize: "11px",
            fontWeight: 600,
            color: "var(--maroon-text)",
          }}
        >
          Cur Non?
        </p>

        <h1
          className="text-center"
          style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: "clamp(24px, 6vw, 34px)",
            fontWeight: 400,
            color: "var(--text-primary)",
            marginTop: "14px",
            lineHeight: 1.2,
          }}
        >
          What can I help you figure out?
        </h1>

        <p
          className="text-center"
          style={{
            fontSize: "14px",
            color: "var(--text-secondary)",
            maxWidth: "460px",
            lineHeight: 1.6,
            marginTop: "12px",
          }}
        >
          Ask about majors, courses, prerequisites, or policies. Every answer is grounded in
          Lafayette&rsquo;s academic sources.
        </p>

        {/* ── Personalized blocks ── */}
        {profile && (
          <div className="w-full flex flex-col gap-3" style={{ maxWidth: "600px", marginTop: "28px" }}>
            {/* Status banner */}
            <div
              className="flex items-center gap-3"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "10px",
                padding: "14px",
              }}
            >
              <div
                className="shrink-0 flex items-center justify-center"
                style={{
                  width: "30px",
                  height: "30px",
                  borderRadius: "999px",
                  background: "rgba(63, 169, 106, 0.14)",
                  color: GREEN,
                }}
                aria-hidden
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>

              <div className="min-w-0 flex-1">
                <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>
                  Personalized advising enabled
                </p>
                <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "1px" }}>
                  Your transcript will be used when relevant.
                </p>
              </div>

              <button
                type="button"
                onClick={onOpenUpload}
                className="shrink-0"
                style={{
                  background: "var(--surface-elevated)",
                  border: "1px solid var(--border)",
                  borderRadius: "7px",
                  fontSize: "11px",
                  color: "var(--text-secondary)",
                  padding: "6px 10px",
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
                Manage Transcript
              </button>
            </div>

            {/* Degree progress */}
            <div
              className="flex items-center gap-4"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "10px",
                padding: "16px",
              }}
            >
              <ProgressDonut pct={pct} />
              <div className="min-w-0">
                <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>
                  {profile.major}
                </p>
                <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "3px" }}>
                  {profile.credits?.applied ?? 0} of {profile.credits?.required ?? 0} credits completed
                </p>
              </div>
            </div>

            <p
              style={{
                fontSize: "10px",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                fontWeight: 600,
                color: "var(--text-secondary)",
                opacity: 0.7,
                marginTop: "6px",
              }}
            >
              Suggested for You
            </p>
          </div>
        )}

        {/* ── Starter cards ── */}
        <div
          className="w-full grid grid-cols-1 sm:grid-cols-2"
          style={{ maxWidth: "600px", gap: "12px", marginTop: profile ? "0px" : "32px" }}
        >
          {prompts.map(({ label, q, icon }) => (
            <button
              key={q}
              type="button"
              onClick={() => onSend(q)}
              className="flex items-start gap-3 text-left"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "10px",
                padding: "16px",
                cursor: "pointer",
                transition: "border-color 160ms ease, background 160ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--maroon)";
                e.currentTarget.style.background = "var(--surface-elevated)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.background = "var(--surface)";
              }}
            >
              <span className="shrink-0" style={{ color: "var(--maroon-text)", lineHeight: 0, marginTop: "1px" }} aria-hidden>
                {icon}
              </span>
              <span className="min-w-0">
                <span className="block" style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                  {label}
                </span>
                <span
                  className="block"
                  style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "3px", lineHeight: 1.5 }}
                >
                  {q}
                </span>
              </span>
            </button>
          ))}
        </div>

        {/* Upload CTA when no profile */}
        {!profile && (
          <button
            type="button"
            onClick={onOpenUpload}
            className="flex items-center gap-2"
            style={{
              marginTop: "20px",
              background: "transparent",
              border: "1px dashed var(--border)",
              borderRadius: "8px",
              padding: "8px 14px",
              fontSize: "12px",
              color: "var(--text-secondary)",
              cursor: "pointer",
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
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Upload your transcript for personalized advising
          </button>
        )}
      </div>
    </div>
  );
}
