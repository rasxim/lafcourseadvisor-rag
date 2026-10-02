"use client";

export default function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-3 animate-fade-in">
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
        <span style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "14px", fontWeight: 600 }}>
          L
        </span>
      </div>
      <div className="flex items-center gap-1.5" style={{ padding: "6px 2px" }} role="status" aria-label="Thinking">
        {[0, 180, 360].map((delay) => (
          <span
            key={delay}
            className="dot-bounce inline-block w-1.5 h-1.5 rounded-full"
            style={{
              background: "var(--text-secondary)",
              animationDelay: `${delay}ms`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
