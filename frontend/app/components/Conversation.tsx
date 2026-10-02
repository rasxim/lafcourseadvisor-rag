"use client";

import { useEffect, useRef } from "react";
import type { Message, Source, StudentProfile } from "./types";
import UserMessage from "./UserMessage";
import AssistantMessage from "./AssistantMessage";
import ThinkingIndicator from "./ThinkingIndicator";

interface ConversationProps {
  messages: Message[];
  loading: boolean;
  profile: StudentProfile | null;
  onSourceClick: (source: Source, index: number) => void;
}

export default function Conversation({ messages, loading, profile, onSourceClick }: ConversationProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto px-4 sm:px-6 py-8 space-y-6" style={{ maxWidth: "820px" }}>
        {messages.map((msg) =>
          msg.role === "user" ? (
            <UserMessage key={msg.id} message={msg} profile={profile} />
          ) : (
            <AssistantMessage key={msg.id} message={msg} onSourceClick={onSourceClick} />
          )
        )}
        {loading && <ThinkingIndicator />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
