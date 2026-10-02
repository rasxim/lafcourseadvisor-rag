"use client";

import { useState, useRef, useEffect } from "react";
import type { StudentProfile } from "./types";

type UploadState = "idle" | "selected" | "uploading" | "success" | "error";

const GREEN = "#3FA96A";
const RED = "#C0392B";

interface TranscriptUploadModalProps {
  onClose: () => void;
  onSuccess: (profile: StudentProfile) => void;
  apiUrl: string;
}

/* ── Stepper ───────────────────────────────────────────────── */

const STEPS = ["Upload", "Process", "Complete"];

function Stepper({ current }: { current: 0 | 1 | 2 }) {
  return (
    <div className="flex items-start" style={{ marginTop: "20px" }}>
      {STEPS.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <div key={label} className="flex items-start flex-1" style={{ minWidth: 0 }}>
            <div className="flex flex-col items-center" style={{ width: "56px", flexShrink: 0 }}>
              <div
                className="flex items-center justify-center"
                style={{
                  width: "22px",
                  height: "22px",
                  borderRadius: "999px",
                  background: done || active ? "var(--maroon)" : "var(--surface-elevated)",
                  color: done || active ? "#fff" : "var(--text-secondary)",
                  border: done || active ? "none" : "1px solid var(--border)",
                  fontSize: "10px",
                  fontWeight: 600,
                  transition: "background 160ms ease, color 160ms ease",
                }}
                aria-current={active ? "step" : undefined}
              >
                {done ? (
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              <span
                style={{
                  fontSize: "10px",
                  marginTop: "6px",
                  color: active || done ? "var(--text-primary)" : "var(--text-secondary)",
                  whiteSpace: "nowrap",
                }}
              >
                {label}
              </span>
            </div>

            {i < STEPS.length - 1 && (
              <div
                aria-hidden
                style={{
                  flex: 1,
                  height: "1px",
                  background: i < current ? "var(--maroon)" : "var(--border)",
                  marginTop: "11px",
                  minWidth: "8px",
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Component ─────────────────────────────────────────────── */

export default function TranscriptUploadModal({ onClose, onSuccess, apiUrl }: TranscriptUploadModalProps) {
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && uploadState !== "uploading") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, uploadState]);

  const step: 0 | 1 | 2 =
    uploadState === "success" ? 2 : uploadState === "uploading" ? 1 : 0;

  function selectFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setErrorMsg("Please choose a PDF file.");
      setUploadState("error");
      return;
    }
    setSelectedFile(file);
    setErrorMsg("");
    setUploadState("selected");
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) selectFile(file);
    e.target.value = "";
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) selectFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) return;
    setUploadState("uploading");
    const form = new FormData();
    form.append("file", selectedFile);
    try {
      const res = await fetch(`${apiUrl}/upload-transcript`, { method: "POST", body: form });
      if (!res.ok) throw new Error("Upload failed");
      const data: StudentProfile = await res.json();
      setProfile(data);
      setUploadState("success");
    } catch {
      setErrorMsg("Couldn't parse that transcript. Make sure it's a PDF degree audit from Lafayette.");
      setUploadState("error");
    }
  }

  function handleRetry() {
    setSelectedFile(null);
    setErrorMsg("");
    setUploadState("idle");
  }

  function handleDone() {
    if (profile) onSuccess(profile);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0"
        style={{ background: "rgba(0,0,0,0.55)" }}
        onClick={uploadState !== "uploading" ? onClose : undefined}
        aria-hidden
      />

      <div
        className="relative w-full"
        style={{
          maxWidth: "460px",
          background: "var(--surface)",
          borderRadius: "14px",
          boxShadow: "var(--shadow-md)",
          border: "1px solid var(--border)",
          padding: "22px",
          maxHeight: "90vh",
          overflowY: "auto",
          animation: "fadeSlideIn 200ms ease both",
        }}
        role="dialog"
        aria-modal="true"
        aria-label="Upload your Lafayette transcript"
      >
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <h2 style={{ fontSize: "17px", fontWeight: 600, color: "var(--text-primary)" }}>
              Upload your Lafayette transcript
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6, marginTop: "6px" }}>
              Your transcript helps personalize your academic advising experience based on your
              completed coursework.
            </p>
          </div>

          {uploadState !== "uploading" && (
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 flex items-center justify-center"
              style={{ width: "28px", height: "28px", borderRadius: "7px", color: "var(--text-secondary)", cursor: "pointer" }}
              aria-label="Close"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Body */}
        <div style={{ marginTop: "18px" }}>
          {/* ── Success ── */}
          {uploadState === "success" && profile ? (
            <div
              style={{
                border: `1px solid ${GREEN}`,
                background: "rgba(63, 169, 106, 0.08)",
                borderRadius: "10px",
                padding: "18px",
              }}
            >
              <div className="flex items-center gap-2.5">
                <div
                  className="shrink-0 flex items-center justify-center"
                  style={{ width: "30px", height: "30px", borderRadius: "999px", background: "rgba(63, 169, 106, 0.16)", color: GREEN }}
                  aria-hidden
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <p style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>
                  Transcript processed
                </p>
              </div>

              <dl style={{ marginTop: "14px", display: "flex", flexDirection: "column", gap: "6px" }}>
                {[
                  ["Name", profile.name],
                  ["Major", profile.major],
                  ["Class year", profile.class_year ? String(profile.class_year) : "—"],
                  [
                    "Credits",
                    `${profile.credits?.applied ?? 0} of ${profile.credits?.required ?? 0} applied`,
                  ],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-baseline gap-2">
                    <dt style={{ fontSize: "11px", color: "var(--text-secondary)", width: "84px", flexShrink: 0 }}>
                      {label}
                    </dt>
                    <dd style={{ fontSize: "13px", color: "var(--text-primary)", minWidth: 0 }}>
                      {value || "—"}
                    </dd>
                  </div>
                ))}
              </dl>

              <button
                type="button"
                onClick={handleDone}
                className="w-full"
                style={{
                  marginTop: "16px",
                  background: "var(--maroon)",
                  color: "#fff",
                  border: "none",
                  borderRadius: "8px",
                  fontSize: "13px",
                  fontWeight: 600,
                  padding: "9px 20px",
                  cursor: "pointer",
                }}
              >
                Start personalized advising
              </button>
            </div>
          ) : uploadState === "error" ? (
            /* ── Error ── */
            <div
              style={{
                border: `1px solid ${RED}`,
                background: "rgba(192, 57, 43, 0.08)",
                borderRadius: "10px",
                padding: "18px",
              }}
            >
              <div className="flex items-start gap-2.5">
                <div className="shrink-0" style={{ color: RED, lineHeight: 0, marginTop: "1px" }} aria-hidden>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                </div>
                <p style={{ fontSize: "13px", color: "var(--text-primary)", lineHeight: 1.6 }}>{errorMsg}</p>
              </div>
              <button
                type="button"
                onClick={handleRetry}
                style={{
                  marginTop: "14px",
                  background: "var(--maroon)",
                  color: "#fff",
                  border: "none",
                  borderRadius: "8px",
                  fontSize: "13px",
                  fontWeight: 600,
                  padding: "9px 20px",
                  cursor: "pointer",
                }}
              >
                Try again
              </button>
            </div>
          ) : (
            /* ── Drop zone ── */
            <>
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                style={{
                  border: `2px dashed ${dragOver ? "var(--maroon)" : "var(--border)"}`,
                  background: dragOver ? "var(--maroon-subtle)" : "transparent",
                  borderRadius: "10px",
                  padding: "32px 16px",
                  textAlign: "center",
                  transition: "border-color 160ms ease, background 160ms ease",
                }}
              >
                <div className="flex flex-col items-center gap-2">
                  <div
                    className="flex items-center justify-center"
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "999px",
                      background: "var(--maroon-subtle)",
                      color: dragOver ? "var(--maroon)" : "var(--maroon-text)",
                    }}
                    aria-hidden
                  >
                    {uploadState === "uploading" ? (
                      <svg className="animate-spin-slow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                      </svg>
                    )}
                  </div>

                  {uploadState === "uploading" ? (
                    <p style={{ fontSize: "13px", color: "var(--text-primary)", marginTop: "4px" }}>
                      Processing your transcript&hellip;
                    </p>
                  ) : (
                    <>
                      <p style={{ fontSize: "13px", color: "var(--text-primary)", marginTop: "4px" }}>
                        {selectedFile ? selectedFile.name : "Drag and drop your transcript here"}
                      </p>
                      <p style={{ fontSize: "11px", color: "var(--text-secondary)" }}>or</p>
                      <button
                        type="button"
                        onClick={() => fileRef.current?.click()}
                        style={{
                          background: "var(--maroon)",
                          color: "#fff",
                          border: "none",
                          borderRadius: "8px",
                          fontSize: "13px",
                          padding: "9px 20px",
                          cursor: "pointer",
                        }}
                      >
                        {selectedFile ? "Choose a different file" : "Choose file"}
                      </button>
                      <p style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "2px" }}>
                        PDF preferred
                      </p>
                    </>
                  )}
                </div>
              </div>

              <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleFileChange} />

              {uploadState === "selected" && selectedFile && (
                <button
                  type="button"
                  onClick={handleUpload}
                  className="w-full"
                  style={{
                    marginTop: "14px",
                    background: "var(--maroon)",
                    color: "#fff",
                    border: "none",
                    borderRadius: "8px",
                    fontSize: "13px",
                    fontWeight: 600,
                    padding: "10px 20px",
                    cursor: "pointer",
                  }}
                >
                  Upload transcript
                </button>
              )}
            </>
          )}
        </div>

        <Stepper current={step} />
      </div>
    </div>
  );
}
