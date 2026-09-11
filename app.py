import json
from pathlib import Path
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Lafayette Course Advisor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Font & background */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #8B0000 0%, #6B0000 100%);
    }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
    [data-testid="stSidebar"] .stMarkdown code {
        background: rgba(255,255,255,0.15);
        color: #FFE4B5 !important;
        border-radius: 4px;
        padding: 1px 5px;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2); }

    /* Progress bar */
    .progress-bar-bg {
        background: rgba(255,255,255,0.2);
        border-radius: 8px;
        height: 8px;
        margin: 4px 0 12px 0;
    }
    .progress-bar-fill {
        background: #FFD700;
        border-radius: 8px;
        height: 8px;
    }

    /* GPA badge */
    .gpa-badge {
        background: rgba(255,215,0,0.25);
        border: 1px solid #FFD700;
        border-radius: 20px;
        padding: 4px 14px;
        font-weight: 700;
        font-size: 1.1rem;
        display: inline-block;
        margin: 4px 0 12px 0;
        color: #FFD700 !important;
    }

    /* Chat header */
    .chat-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 20px 0 8px 0;
        border-bottom: 2px solid #8B0000;
        margin-bottom: 20px;
    }
    .chat-header h1 {
        font-size: 1.8rem;
        font-weight: 700;
        color: #8B0000;
        margin: 0;
    }
    .chat-header p {
        font-size: 0.9rem;
        color: #666;
        margin: 0;
    }

    /* Sample question buttons */
    .stButton > button {
        border: 1.5px solid #8B0000 !important;
        color: #8B0000 !important;
        background: white !important;
        border-radius: 20px !important;
        font-size: 0.82rem !important;
        padding: 6px 14px !important;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #8B0000 !important;
        color: white !important;
    }

    /* Source expander */
    .source-chip {
        background: #f0f2f6;
        border-radius: 12px;
        padding: 3px 10px;
        font-size: 0.75rem;
        color: #555;
        display: inline-block;
        margin: 2px;
    }

    /* Hide streamlit branding */
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Load pipeline ──────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading advisor...")
def load_pipeline():
    from rag import ask, STUDENT_PROFILE
    from retriever import Retriever
    retriever = Retriever()
    return ask, retriever, STUDENT_PROFILE

ask, retriever, profile = load_pipeline()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Lafayette College")

    st.markdown("---")

    # Student card
    first_name = profile["name"].split()[0]
    st.markdown(f"## {first_name}")
    st.markdown(f"**{profile['major']}**")
    st.markdown(f"Class of {profile['class_year']}  ·  Lafayette College")

    st.markdown("---")

    # GPA
    st.markdown("**Overall GPA**")
    st.markdown(f'<div class="gpa-badge">{profile["overall_gpa"]}</div>', unsafe_allow_html=True)

    # Credits progress
    applied  = profile["credits"]["applied"]
    required = profile["credits"]["required"]
    pct      = min(int(applied / required * 100), 100)
    st.markdown(f"**Credits Completed** — {applied} / {required}")
    st.markdown(f"""
    <div class="progress-bar-bg">
        <div class="progress-bar-fill" style="width:{pct}%"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Completed courses
    st.markdown("**Completed Courses**")
    for course in profile["completed_courses"]:
        grade_color = "#2ecc71" if course["grade"].startswith("A") else "#f39c12"
        st.markdown(
            f'`{course["code"]}` {course["title"]} '
            f'<span style="color:{grade_color};font-weight:700">{course["grade"]}</span>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # In progress
    st.markdown("**In Progress — Fall 2026**")
    for course in profile["in_progress_courses"]:
        st.markdown(f'`{course["code"]}` {course["title"]}')

    st.markdown("---")
    st.caption("LlamaParse · ChromaDB · Gemini · Streamlit")

# ── Main Chat ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="chat-header">
    <div>
        <h1>Lafayette Course Advisor</h1>
        <p>AI-powered degree planning assistant — ask about requirements, prerequisites, and graduation planning.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Sample questions
st.markdown("**Try asking:**")
samples = [
    "What CS courses do I still need to graduate?",
    "What are the prerequisites for CS 301?",
    "What counts toward the writing requirement?",
    "Do I still need a statistics course?",
    "What CS electives are available at the 400 level?",
    "How many credits do I have left?",
]
cols = st.columns(3)
for i, sample in enumerate(samples):
    if cols[i % 3].button(sample, key=f"sample_{i}", use_container_width=True):
        st.session_state.pending_query = sample

st.markdown("---")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                f"Hi {first_name}! I'm your Lafayette degree advisor. "
                f"I can help you track your **{profile['major']}** requirements, "
                f"check prerequisites, and plan your path to graduation. "
                f"What would you like to know?"
            ),
        }
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("context"):
            with st.expander("Sources", expanded=False):
                for chunk in msg["context"]:
                    st.markdown(
                        f'<span class="source-chip">Page {chunk.get("start_page") or chunk["metadata"].get("start_page", "?")}</span>'
                        f'<span class="source-chip">{chunk["metadata"]["section_type"]}</span>'
                        f'<span class="source-chip">score {chunk["score"]}</span>',
                        unsafe_allow_html=True
                    )
                    st.markdown(chunk["text"][:300] + "...")
                    st.divider()

# Input
if "pending_query" in st.session_state:
    prompt = st.session_state.pop("pending_query")
else:
    prompt = st.chat_input("Ask about your degree requirements...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching catalog..."):
            chunks = retriever.retrieve(prompt)
            answer = ask(prompt)

        st.markdown(answer)

        if chunks:
            with st.expander("Sources", expanded=False):
                for chunk in chunks:
                    st.markdown(
                        f'<span class="source-chip">Page {chunk.get("start_page") or chunk["metadata"].get("start_page", "?")}</span>'
                        f'<span class="source-chip">{chunk["metadata"]["section_type"]}</span>'
                        f'<span class="source-chip">score {chunk["score"]}</span>',
                        unsafe_allow_html=True
                    )
                    st.markdown(chunk["text"][:300] + "...")
                    st.divider()

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "context": chunks,
    })
