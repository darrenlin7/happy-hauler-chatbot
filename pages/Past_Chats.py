"""
Past_Chats.py — Streamlit page displaying all completed screening sessions.

Accessible from the sidebar navigation automatically (Streamlit multipage).
Runs: streamlit run app.py  (no separate command needed)
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st

from database import get_all_sessions, init_db

_ET = ZoneInfo("America/New_York")


def _to_et(iso: str) -> str:
    """Convert a UTC ISO timestamp string to Eastern Time for display."""
    if not iso:
        return "—"
    dt_utc = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
    dt_et = dt_utc.astimezone(_ET)
    # e.g. "2026-03-10 03:00 PM ET"
    return dt_et.strftime("%Y-%m-%d %I:%M %p ET")

init_db()

st.title("Past Chat Sessions")
st.caption("All completed candidate conversations, most recent first.")

sessions = get_all_sessions()

if not sessions:
    st.info(
        "No completed sessions yet. Run a screening on the **Chat** page to get started."
    )
    st.stop()

for session in sessions:
    # ── Metadata ──────────────────────────────────────────────────────────────
    created = _to_et(session["created_at"])
    ended = _to_et(session.get("ended_at") or "")
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
        col1, col2 = st.columns(2)
        col1.metric("Outcome", badge.split()[1])
        col2.markdown(
            f"<div style='text-align:right'>"
            f"<small><b>Started:</b> {created}</small><br>"
            f"<small><b>Ended:</b> {ended or '—'}</small>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.write("**Summary**")
        st.write(summary)

        st.divider()
        st.write("**Full Conversation**")

        for msg in messages:
            avatar = "🚛" if msg["role"] == "assistant" else "👤"
            with st.chat_message(msg["role"], avatar=avatar):
                st.write(msg["content"])
