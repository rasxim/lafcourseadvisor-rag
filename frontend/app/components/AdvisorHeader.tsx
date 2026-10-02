"use client";

import type { StudentProfile } from "./types";
import { CATALOG_LABEL, initialsFrom } from "./utils";

interface AdvisorHeaderProps {
  theme: "light" | "dark";
  profile: StudentProfile | null;
  onThemeToggle: () => void;
  onToggleSidebar: () => void;
}

export default function AdvisorHeader({
  theme,
  profile,
  onThemeToggle,
  onToggleSidebar,
}: AdvisorHeaderProps) {
  const isDark = theme === "dark";
  const initials = initialsFrom(profile?.name);

  return (
    <header
      className="flex items-center gap-2 shrink-0"
      style={{
        height: "52px",
        padding: "0 12px",
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      {/* Mobile hamburger */}
      <button
        type="button"
        onClick={onToggleSidebar}
        className="sm:hidden flex items-center justify-center shrink-0"
        style={{ width: "32px", height: "32px", borderRadius: "8px", color: "var(--text-secondary)", cursor: "pointer" }}
        aria-label="Open menu"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      <div className="flex-1" />

      {/* ── Catalog pill (static indicator) ── */}
      <div
        className="hidden sm:flex items-center gap-1.5 shrink-0"
        style={{
          background: "var(--surface-elevated)",
          border: "1px solid var(--border)",
          borderRadius: "7px",
          padding: "5px 10px",
          fontSize: "12px",
          color: "var(--text-secondary)",
        }}
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        <span style={{ whiteSpace: "nowrap" }}>{CATALOG_LABEL}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>

      {/* ── Theme switch ── */}
      <button
        type="button"
        role="switch"
        aria-checked={isDark}
        onClick={onThemeToggle}
        className="relative shrink-0 flex items-center"
        style={{
          width: "44px",
          height: "24px",
          borderRadius: "999px",
          background: "var(--surface-elevated)",
          border: "1px solid var(--border)",
          cursor: "pointer",
          padding: 0,
        }}
        aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      >
        <span
          aria-hidden
          className="absolute flex items-center justify-center"
          style={{ left: "4px", top: 0, bottom: 0, color: "var(--text-secondary)" }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="4" />
            <line x1="12" y1="2" x2="12" y2="4" />
            <line x1="12" y1="20" x2="12" y2="22" />
            <line x1="4.9" y1="4.9" x2="6.3" y2="6.3" />
            <line x1="17.7" y1="17.7" x2="19.1" y2="19.1" />
            <line x1="2" y1="12" x2="4" y2="12" />
            <line x1="20" y1="12" x2="22" y2="12" />
            <line x1="4.9" y1="19.1" x2="6.3" y2="17.7" />
            <line x1="17.7" y1="6.3" x2="19.1" y2="4.9" />
          </svg>
        </span>
        <span
          aria-hidden
          className="absolute"
          style={{
            width: "18px",
            height: "18px",
            borderRadius: "999px",
            background: "#FFFFFF",
            boxShadow: "var(--shadow-sm)",
            top: "2px",
            left: isDark ? "22px" : "2px",
            transition: "left 180ms ease",
          }}
        />
      </button>

      {/* ── Avatar ── */}
      <div
        className="shrink-0 flex items-center justify-center"
        style={{
          width: "30px",
          height: "30px",
          borderRadius: "999px",
          background: "var(--maroon)",
          color: "#fff",
        }}
        title={profile?.name ?? "Not signed in"}
        aria-label={profile?.name ? `Signed in as ${profile.name}` : "No transcript loaded"}
      >
        {initials ? (
          <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.02em" }}>{initials}</span>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        )}
      </div>
    </header>
  );
}
