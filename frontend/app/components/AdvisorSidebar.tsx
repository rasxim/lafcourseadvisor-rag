"use client";

import type { Message, StudentProfile } from "./types";
import { firstNameFrom } from "./utils";

/* ── Icons ─────────────────────────────────────────────────── */

const ICON_PROPS = {
  width: 15,
  height: 15,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const IconPlus = (
  <svg {...ICON_PROPS}>
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const IconGraduationCap = (
  <svg {...ICON_PROPS}>
    <path d="M22 10 12 5 2 10l10 5 10-5Z" />
    <path d="M6 12v5c0 1 2.7 2.5 6 2.5s6-1.5 6-2.5v-5" />
  </svg>
);

const IconBook = (
  <svg {...ICON_PROPS}>
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" />
  </svg>
);

const IconDocument = (
  <svg {...ICON_PROPS}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
  </svg>
);

const IconCalendar = (
  <svg {...ICON_PROPS}>
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" />
    <line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const IconUpload = (
  <svg {...ICON_PROPS}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
);

const IconChatBubble = (
  <svg {...ICON_PROPS} width={13} height={13}>
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z" />
  </svg>
);

/* ── Nav data ──────────────────────────────────────────────── */

const EXPLORE_ITEMS = [
  {
    label: "Majors & Minors",
    q: "What majors and minors does Lafayette College offer?",
    icon: IconGraduationCap,
  },
  {
    label: "Course Catalog",
    q: "Show me an overview of the Lafayette course catalog and how to search for courses.",
    icon: IconBook,
  },
  {
    label: "Academic Policies",
    q: "What are Lafayette's key academic policies around grades, withdrawals, and academic standing?",
    icon: IconDocument,
  },
  {
    label: "Degree Planning",
    q: "How does degree planning work at Lafayette? What should I consider when planning my four years?",
    icon: IconCalendar,
  },
];

/* ── Pieces ────────────────────────────────────────────────── */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="px-3"
      style={{
        fontSize: "10px",
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        color: "var(--text-secondary)",
        opacity: 0.7,
        marginTop: "16px",
        marginBottom: "6px",
        fontWeight: 600,
      }}
    >
      {children}
    </p>
  );
}

function NavItem({
  icon,
  label,
  collapsed,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  collapsed: boolean;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={collapsed ? label : undefined}
      aria-label={collapsed ? label : undefined}
      className="w-full flex items-center gap-2.5 text-left"
      style={{
        height: "34px",
        borderRadius: "8px",
        padding: collapsed ? "0" : "0 12px",
        justifyContent: collapsed ? "center" : "flex-start",
        background: active ? "var(--maroon)" : "transparent",
        color: active ? "#fff" : "var(--text-secondary)",
        cursor: "pointer",
        transition: "background 160ms ease, color 160ms ease",
      }}
      onMouseEnter={(e) => {
        if (active) return;
        e.currentTarget.style.background = "var(--surface-elevated)";
        e.currentTarget.style.color = "var(--text-primary)";
      }}
      onMouseLeave={(e) => {
        if (active) return;
        e.currentTarget.style.background = "transparent";
        e.currentTarget.style.color = "var(--text-secondary)";
      }}
    >
      <span className="shrink-0 flex items-center">{icon}</span>
      {!collapsed && (
        <span className="truncate" style={{ fontSize: "13px", fontWeight: active ? 500 : 400 }}>
          {label}
        </span>
      )}
    </button>
  );
}

/* ── Component ─────────────────────────────────────────────── */

interface AdvisorSidebarProps {
  open: boolean;
  collapsed: boolean;
  onCollapse: () => void;
  messages: Message[];
  profile: StudentProfile | null;
  onSend: (query: string) => void;
  onOpenUpload: () => void;
  onNewChat: () => void;
  onClose: () => void;
  isMobile: boolean;
}

export default function AdvisorSidebar({
  open,
  collapsed,
  onCollapse,
  messages,
  profile,
  onSend,
  onOpenUpload,
  onNewChat,
  onClose,
  isMobile,
}: AdvisorSidebarProps) {
  const width = collapsed ? 52 : 232;

  const recent = messages
    .filter((m) => m.role === "user")
    .slice(-5)
    .reverse();

  const sidebarContent = (
    <aside
      className="flex flex-col h-full"
      style={{
        width: isMobile ? "248px" : `${width}px`,
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        overflow: "hidden",
        transition: "width 200ms ease",
        flexShrink: 0,
      }}
    >
      {/* ── Wordmark ── */}
      <div
        className="shrink-0 flex items-start justify-between"
        style={{
          padding: collapsed ? "16px 8px" : "16px 12px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        {collapsed ? (
          <div className="w-full flex justify-center">
            <span
              style={{
                color: "var(--maroon-text)",
                fontFamily: "Georgia, 'Times New Roman', serif",
                fontWeight: 600,
                fontSize: "18px",
              }}
            >
              L
            </span>
          </div>
        ) : (
          <div className="min-w-0">
            <p
              style={{
                fontFamily: "Georgia, 'Times New Roman', serif",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--maroon-text)",
                fontSize: "18px",
                fontWeight: 600,
                lineHeight: 1.1,
              }}
            >
              Lafayette
            </p>
            <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-primary)", marginTop: "3px" }}>
              Academic Advisor
            </p>
            <p
              style={{
                fontFamily: "Georgia, 'Times New Roman', serif",
                fontStyle: "italic",
                fontSize: "11px",
                color: "var(--text-secondary)",
                marginTop: "1px",
              }}
            >
              Cur Non?
            </p>
          </div>
        )}

        {/* Collapse (desktop) / close (mobile) */}
        {isMobile ? (
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 flex items-center justify-center"
            style={{ width: "26px", height: "26px", borderRadius: "6px", color: "var(--text-secondary)", cursor: "pointer" }}
            aria-label="Close menu"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        ) : (
          !collapsed && (
            <button
              type="button"
              onClick={onCollapse}
              className="shrink-0 flex items-center justify-center"
              style={{
                width: "24px",
                height: "24px",
                borderRadius: "6px",
                color: "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "14px",
                lineHeight: 1,
              }}
              aria-label="Collapse sidebar"
              title="Collapse sidebar"
            >
              &#171;
            </button>
          )
        )}
      </div>

      {/* Expand button when collapsed */}
      {!isMobile && collapsed && (
        <div className="shrink-0 flex justify-center" style={{ paddingTop: "8px" }}>
          <button
            type="button"
            onClick={onCollapse}
            className="flex items-center justify-center"
            style={{
              width: "26px",
              height: "26px",
              borderRadius: "6px",
              color: "var(--text-secondary)",
              cursor: "pointer",
              fontSize: "14px",
              lineHeight: 1,
            }}
            aria-label="Expand sidebar"
            title="Expand sidebar"
          >
            &#187;
          </button>
        </div>
      )}

      {/* ── Scrollable nav ── */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden" style={{ padding: collapsed ? "8px 6px" : "8px" }}>
        <div className="flex flex-col gap-0.5">
          <NavItem
            icon={IconPlus}
            label="New Chat"
            collapsed={collapsed}
            active
            onClick={() => {
              onNewChat();
              if (isMobile) onClose();
            }}
          />
          {EXPLORE_ITEMS.map((item) => (
            <NavItem
              key={item.label}
              icon={item.icon}
              label={item.label}
              collapsed={collapsed}
              onClick={() => {
                onSend(item.q);
                if (isMobile) onClose();
              }}
            />
          ))}
        </div>

        {/* PERSONALIZATION */}
        {!collapsed && <SectionLabel>Personalization</SectionLabel>}
        {profile ? (
          <button
            type="button"
            onClick={() => {
              onOpenUpload();
              if (isMobile) onClose();
            }}
            title={collapsed ? "Personalized — manage transcript" : undefined}
            aria-label={collapsed ? "Personalized, manage transcript" : undefined}
            className="w-full flex items-center gap-2.5 text-left"
            style={{
              borderRadius: "8px",
              padding: collapsed ? "6px 0" : "6px 12px",
              justifyContent: collapsed ? "center" : "flex-start",
              background: "transparent",
              cursor: "pointer",
              transition: "background 160ms ease",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "var(--surface-elevated)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
          >
            <span className="shrink-0 flex items-center" style={{ color: "var(--maroon-text)" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </span>
            {!collapsed && (
              <span className="min-w-0">
                <span className="block truncate" style={{ fontSize: "12px", fontWeight: 600, color: "var(--maroon-text)" }}>
                  Personalized
                </span>
                <span className="block truncate" style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                  {firstNameFrom(profile.name)} &middot; {profile.major}
                </span>
              </span>
            )}
          </button>
        ) : (
          <NavItem
            icon={IconUpload}
            label="Upload Transcript"
            collapsed={collapsed}
            onClick={() => {
              onOpenUpload();
              if (isMobile) onClose();
            }}
          />
        )}

        {/* RECENT CONVERSATIONS */}
        {!collapsed && recent.length > 0 && (
          <>
            <SectionLabel>Recent Conversations</SectionLabel>
            <div className="flex flex-col gap-0.5">
              {recent.map((m) => (
                <NavItem
                  key={m.id}
                  icon={IconChatBubble}
                  label={m.content}
                  collapsed={false}
                  onClick={() => {
                    onSend(m.content);
                    if (isMobile) onClose();
                  }}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* ── Footer ── */}
      <div
        className="shrink-0 relative flex items-end"
        style={{
          height: "90px",
          borderTop: "1px solid var(--border)",
          padding: collapsed ? "0 8px 12px" : "0 14px 14px",
        }}
      >
        <div
          aria-hidden
          className="absolute inset-0 pointer-events-none"
          style={{
            background: "linear-gradient(to top, var(--maroon-dark), transparent)",
            opacity: 0.35,
          }}
        />
        {!collapsed && (
          <div
            className="relative"
            style={{
              fontFamily: "Georgia, 'Times New Roman', serif",
              fontSize: "12px",
              fontWeight: 500,
              color: "var(--text-primary)",
              lineHeight: 1.45,
            }}
          >
            <span className="block">Great Minds</span>
            <span className="block">Brighter Futures</span>
          </div>
        )}
      </div>
    </aside>
  );

  // Mobile: off-canvas drawer with scrim
  if (isMobile) {
    if (!open) return null;
    return (
      <>
        <div
          className="fixed inset-0 z-30"
          style={{ background: "rgba(0,0,0,0.45)" }}
          onClick={onClose}
          aria-hidden
        />
        <div className="fixed left-0 top-0 bottom-0 z-40" style={{ animation: "slideInLeft 180ms ease both" }}>
          <style>{`@keyframes slideInLeft { from { transform: translateX(-100%); } to { transform: translateX(0); } }`}</style>
          {sidebarContent}
        </div>
      </>
    );
  }

  if (!open) return null;
  return sidebarContent;
}
