"use client";

import type { Message, StudentProfile } from "./types";
import { formatTime, initialsFrom } from "./utils";

interface UserMessageProps {
  message: Message;
  profile: StudentProfile | null;
}

export default function UserMessage({ message, profile }: UserMessageProps) {
  const initials = initialsFrom(profile?.name);

  return (
    <div className="flex justify-end animate-fade-in">
      <div className="flex items-start gap-2.5" style={{ maxWidth: "100%" }}>
        <div className="flex flex-col items-end min-w-0">
          <div
            style={{
              background: "var(--maroon)",
              color: "#fff",
              fontSize: "14px",
              lineHeight: 1.6,
              borderRadius: "12px 12px 4px 12px",
              padding: "10px 14px",
              maxWidth: "78vw",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {message.content}
          </div>
          <span style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "4px" }}>
            {formatTime(message.createdAt)}
          </span>
        </div>

        <div
          className="shrink-0 flex items-center justify-center"
          style={{
            width: "28px",
            height: "28px",
            borderRadius: "999px",
            background: "var(--maroon)",
            color: "#fff",
          }}
          aria-hidden
        >
          {initials ? (
            <span style={{ fontSize: "10px", fontWeight: 700 }}>{initials}</span>
          ) : (
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          )}
        </div>
      </div>
    </div>
  );
}
