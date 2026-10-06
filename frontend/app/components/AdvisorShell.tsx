"use client";

import { useState, useEffect, useCallback } from "react";
import type { Message, Source, StudentProfile } from "./types";
import AdvisorHeader from "./AdvisorHeader";
import AdvisorSidebar from "./AdvisorSidebar";
import WelcomeState from "./WelcomeState";
import Conversation from "./Conversation";
import ChatComposer from "./ChatComposer";
import SourceDrawer from "./SourceDrawer";
import TranscriptUploadModal from "./TranscriptUploadModal";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type ActiveSource = { source: Source; index: number };

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 639px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return isMobile;
}

export default function AdvisorShell() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [activeSource, setActiveSource] = useState<ActiveSource | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const isMobile = useIsMobile();

  // Load theme from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem("theme");
      const initial =
        saved === "light" || saved === "dark"
          ? saved
          : window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light";
      setTheme(initial);
    } catch {
      setTheme("light");
    }
  }, []);

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("theme", theme); } catch {}
  }, [theme]);

  // On mobile: sidebar closed by default
  useEffect(() => {
    setSidebarOpen(!isMobile);
  }, [isMobile]);

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setInput("");
    setActiveSource(null);
  }, []);

  const handleSourceClick = useCallback((source: Source, index: number) => {
    setActiveSource({ source, index });
  }, []);

  const sendMessage = useCallback(async (query: string) => {
    if (!query.trim() || loading) return;
    setInput("");
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: query,
      createdAt: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    if (isMobile) setSidebarOpen(false);
    try {
      const res = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, student_profile: profile ?? {} }),
      });
      if (!res.ok) throw new Error("API error");
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: data.answer,
          sources: data.sources ?? [],
          createdAt: Date.now(),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: "assistant",
          content: "Something went wrong. Please try again.",
          createdAt: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [loading, profile, isMobile]);

  const handleFileForUpload = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API_URL}/upload-transcript`, { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : "");
      }
      const data: StudentProfile = await res.json();
      setProfile(data);
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          role: "assistant",
          content: `Got it! I loaded the transcript for **${data.name}** (${data.major}, Class of ${data.class_year}). Ask me what requirements you still need to complete, or anything else about your degree.`,
          createdAt: Date.now(),
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content:
            (e instanceof Error && e.message) ||
            "Couldn't parse that transcript. Make sure it's a PDF degree audit from Lafayette.",
          createdAt: Date.now(),
        },
      ]);
    }
  }, []);

  const handleUploadSuccess = useCallback((newProfile: StudentProfile) => {
    setProfile(newProfile);
    setMessages((prev) => [
      ...prev,
      {
        id: `sys-${Date.now()}`,
        role: "assistant",
        content: `Got it! I loaded the transcript for **${newProfile.name}** (${newProfile.major}, Class of ${newProfile.class_year}). Ask me what requirements you still need to complete, or anything else about your degree.`,
        createdAt: Date.now(),
      },
    ]);
  }, []);

  function handleDragOverPage(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileForUpload(file);
  }

  return (
    <div
      className="flex h-full overflow-hidden"
      style={{ background: "var(--bg)" }}
      onDragOver={handleDragOverPage}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {dragOver && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: "rgba(0,0,0,0.7)" }}
        >
          <div
            className="flex flex-col items-center gap-3"
            style={{
              border: "2px dashed var(--maroon)",
              background: "var(--surface)",
              borderRadius: "14px",
              padding: "32px 40px",
            }}
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--maroon)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p style={{ fontSize: "14px", fontWeight: 600, color: "var(--maroon-text)" }}>
              Drop your transcript here
            </p>
          </div>
        </div>
      )}

      {/* Sidebar */}
      <AdvisorSidebar
        open={sidebarOpen}
        collapsed={isMobile ? false : sidebarCollapsed}
        onCollapse={() => setSidebarCollapsed((v) => !v)}
        messages={messages}
        profile={profile}
        onSend={sendMessage}
        onOpenUpload={() => setUploadModalOpen(true)}
        onNewChat={handleNewChat}
        onClose={() => setSidebarOpen(false)}
        isMobile={isMobile}
      />

      {/* Main column */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <AdvisorHeader
          theme={theme}
          profile={profile}
          onThemeToggle={toggleTheme}
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
        />

        {messages.length === 0 ? (
          <WelcomeState
            profile={profile}
            onSend={sendMessage}
            onOpenUpload={() => setUploadModalOpen(true)}
          />
        ) : (
          <Conversation
            messages={messages}
            loading={loading}
            profile={profile}
            onSourceClick={handleSourceClick}
          />
        )}

        <ChatComposer
          input={input}
          loading={loading}
          profile={profile}
          onChange={setInput}
          onSend={() => sendMessage(input)}
          onFileSelect={handleFileForUpload}
          onOpenUpload={() => setUploadModalOpen(true)}
        />
      </div>

      {/* Source drawer */}
      <SourceDrawer source={activeSource?.source ?? null} onClose={() => setActiveSource(null)} />

      {/* Upload modal */}
      {uploadModalOpen && (
        <TranscriptUploadModal
          onClose={() => setUploadModalOpen(false)}
          onSuccess={handleUploadSuccess}
          apiUrl={API_URL}
        />
      )}
    </div>
  );
}
