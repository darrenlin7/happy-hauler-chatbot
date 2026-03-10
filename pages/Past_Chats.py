"""
Past_Chats.py — Streamlit page displaying all completed screening sessions.

Accessible from the sidebar navigation automatically (Streamlit multipage).
Runs: streamlit run app.py  (no separate command needed)
"""

import streamlit as st

from database import get_all_sessions, init_db

st.set_page_config(
    page_title="Past Chats — Happy Hauler",
    page_icon="📋",
    layout="centered",
)

init_db()

st.title("📋 Past Screening Sessions")
st.caption("All completed candidate conversations, most recent first.")

sessions = get_all_sessions()

if not sessions:
    st.info(
        "No completed sessions yet. Run a screening on the **Chat** page to get started."
    )
    st.stop()

for session in sessions:
    # ── Metadata ──────────────────────────────────────────────────────────────
    created = session["created_at"][:16].replace("T", " ")
    ended = (session.get("ended_at") or "")[:16].replace("T", " ")
    passed = session["passed"]
    summary = session.get("summary") or "No summary available."
    messages = session.get("messages", [])

    if passed == 1:
        badge = "✅ PASSED"
    elif passed == 0:
        badge = "❌ FAILED"
    else:
        badge = "⏳ INCOMPLETE"

    # Truncated summary as the expander label
    preview = (summary[:110] + "…") if len(summary) > 110 else summary
    expander_label = f"{badge}  |  {created}  —  {preview}"

    with st.expander(expander_label):
        col1, col2, col3 = st.columns(3)
        col1.metric("Outcome", badge.split()[1])
        col2.metric("Started", created)
        col3.metric("Ended", ended or "—")

        st.write("**Summary**")
        st.write(summary)

        st.divider()
        st.write("**Full Conversation**")

        for msg in messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
