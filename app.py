"""
app.py — Streamlit UI for the Lafayette College Course Advisor RAG pipeline.
Run with: streamlit run app.py
"""

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

# ── Load pipeline (cached so model loads once) ─────────────────────────────────
@st.cache_resource(show_spinner="Loading advisor...")
def load_pipeline():
    from rag import ask, STUDENT_PROFILE
    from retriever import Retriever
    retriever = Retriever()
    return ask, retriever, STUDENT_PROFILE

ask, retriever, profile = load_pipeline()

# ── Sidebar — Student Profile ──────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/en/thumb/6/6e/Lafayette_College_leopard_logo.svg/200px-Lafayette_College_leopard_logo.svg.png",
        width=80,
    )
    st.title("Lafayette College")
    st.caption("AI Course Advisor")
    st.divider()

    st.subheader("Student Profile")
    st.markdown(f"**Name:** {profile['name']}")
    st.markdown(f"**Major:** {profile['major']}")
    st.markdown(f"**Class of:** {profile['class_year']}")
    st.markdown(f"**GPA:** {profile['overall_gpa']}")
    st.markdown(f"**Credits:** {profile['credits']['applied']} / {profile['credits']['required']}")

    st.divider()
    st.subheader("Completed Courses")
    for course in profile["completed_courses"]:
        st.markdown(f"- `{course['code']}` {course['title']} — **{course['grade']}**")

    st.divider()
    st.subheader("In Progress (Fall 2026)")
    for course in profile["in_progress_courses"]:
        st.markdown(f"- `{course['code']}` {course['title']}")

    st.divider()
    st.caption("Powered by LlamaParse · ChromaDB · Gemini")

# ── Main — Chat Interface ──────────────────────────────────────────────────────
st.title("🎓 Lafayette Course Advisor")
st.caption("Ask me anything about your degree requirements, course prerequisites, or graduation planning.")

# Sample questions
with st.expander("💡 Try asking...", expanded=False):
    cols = st.columns(2)
    samples = [
        "What CS courses do I still need to graduate?",
        "What are the prerequisites for CS 301?",
        "Do I still need a statistics course?",
        "What counts toward the writing requirement?",
        "Have I satisfied the science lab requirement?",
        "How many credits do I have left?",
    ]
    for i, sample in enumerate(samples):
        if cols[i % 2].button(sample, key=f"sample_{i}", use_container_width=True):
            st.session_state.pending_query = sample

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": f"Hi {profile['name'].split()[2]}! 👋 I'm your Lafayette degree advisor. I can help you track your CS requirements, check prerequisites, and plan your path to graduation. What would you like to know?",
        }
    ]

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("context"):
            with st.expander("📚 Sources used", expanded=False):
                for chunk in msg["context"]:
                    st.caption(f"Page {chunk['metadata']['page']} · {chunk['metadata']['section_type']} · score {chunk['score']}")
                    st.markdown(chunk["text"][:300] + "...")
                    st.divider()

# Handle sample button click
if "pending_query" in st.session_state:
    prompt = st.session_state.pop("pending_query")
else:
    prompt = st.chat_input("Ask about your degree requirements...")

if prompt:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get answer
    with st.chat_message("assistant"):
        with st.spinner("Searching catalog..."):
            chunks  = retriever.retrieve(prompt)
            answer  = ask(prompt)

        st.markdown(answer)

        if chunks:
            with st.expander("📚 Sources used", expanded=False):
                for chunk in chunks:
                    st.caption(f"Page {chunk['metadata']['page']} · {chunk['metadata']['section_type']} · score {chunk['score']}")
                    st.markdown(chunk["text"][:300] + "...")
                    st.divider()

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "context": chunks,
    })
