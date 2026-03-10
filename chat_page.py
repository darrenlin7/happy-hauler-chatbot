"""
chat_page.py — Chat UI for the Happy Hauler recruiting chatbot.

Loaded by app.py via st.navigation — do not run this file directly.
"""

from __future__ import annotations

import streamlit as st

from config import State
from database import create_session, init_db, save_session
from llm import (
    answer_faq_question,
    generate_closing,
    generate_summary,
    interpret_response,
)
from state_machine import ConversationStateMachine

init_db()

# ─── Static screening prompts (hardcoded — zero latency, perfectly consistent) ─

_INITIAL_GREETING = (
    "Hi! I'm the Happy Hauler recruiting assistant. Thanks for your interest "
    "in our Class A CDL truck driver role. Can I ask you a few quick screening "
    "questions?"
)

_GREETING_REPROMPT = (
    "No problem! Just say 'yes' or 'ready' whenever you'd like to begin."
)

_STATE_PROMPTS: dict[State, str] = {
    State.ASKING_CDL: "Do you have a valid Class A CDL?",
    State.ASKING_OVERNIGHT: (
        "This role requires being on the road for two nights each week. "
        "Is that okay with you?"
    ),
    State.QA_OPEN: (
        "Do you have any questions about the role or Happy Hauler Trucking Co.?"
    ),
}

_EXPERIENCE_FOLLOWUPS = [
    "Could you give me an exact number of years? For example, '3 years' or '5 years'.",
    (
        "I need a specific number to move forward — how many years have you been "
        "driving a commercial truck?"
    ),
]


# ─── Session state helpers ────────────────────────────────────────────────────

def _init_session() -> None:
    if "sm" not in st.session_state:
        st.session_state.sm = ConversationStateMachine()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = create_session()
    if "saved" not in st.session_state:
        st.session_state.saved = False


def _add_message(role: str, content: str) -> None:
    st.session_state.messages.append({"role": role, "content": content})


def _bot(text: str) -> None:
    _add_message("assistant", text)
    with st.chat_message("assistant"):
        st.write(text)


# ─── Screening prompt picker ──────────────────────────────────────────────────

def _screening_prompt(sm: ConversationStateMachine) -> str:
    state = sm.state

    if state == State.GREETING:
        return _GREETING_REPROMPT

    if state == State.ASKING_EXPERIENCE:
        if sm.follow_up_count > 0:
            idx = min(sm.follow_up_count - 1, len(_EXPERIENCE_FOLLOWUPS) - 1)
            return _EXPERIENCE_FOLLOWUPS[idx]
        return "How many years of truck driving experience do you have?"

    if state in _STATE_PROMPTS:
        return _STATE_PROMPTS[state]

    if state == State.ENDED:
        return generate_closing(sm.passed, sm.fail_reason)

    return ""


# ─── Page ─────────────────────────────────────────────────────────────────────

_init_session()

sm: ConversationStateMachine = st.session_state.sm

st.title("Happy Hauler Recruiting Assistant")

# ── End-of-conversation UI ────────────────────────────────────────────────────
if sm.state == State.ENDED:
    if not st.session_state.saved:
        summary = generate_summary(
            st.session_state.messages,
            sm.passed,
            sm.experience_years,
        )
        save_session(
            st.session_state.session_id,
            st.session_state.messages,
            summary,
            sm.passed,
        )
        st.session_state.saved = True
        st.session_state.summary = summary

    if sm.passed:
        st.success("✅  **PASSED** — Candidate meets initial qualifications.")
    else:
        st.error("❌  **FAILED** — Candidate does not meet minimum requirements.")

    st.write(st.session_state.get("summary", ""))

    if st.button("Start New Conversation", type="primary"):
        for key in ("sm", "messages", "session_id", "saved", "summary"):
            st.session_state.pop(key, None)
        st.rerun()

else:
    # Show initial greeting on the very first page load
    if not st.session_state.messages:
        _add_message("assistant", _INITIAL_GREETING)

    # Render message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # ── Chat input ────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Type your response here…"):
        _add_message("user", prompt)
        with st.chat_message("user", avatar="👷"):
            st.write(prompt)

        prev_state = sm.state

        interpretation = interpret_response(prev_state, prompt)
        intent = interpretation.get("intent", "vague")
        extracted_value = interpretation.get("extracted_value")

        if prev_state == State.QA_OPEN:
            if intent == "question":
                answer = answer_faq_question(prompt, st.session_state.messages[:-1])
                _bot(answer)
                _bot("Is there anything else you'd like to know, or are you all set?")
                st.stop()

            if intent == "yes":
                _bot("Sure! What would you like to know?")
                st.stop()

        sm.process(intent, extracted_value)

        response = _screening_prompt(sm)
        if response:
            _bot(response)

        if sm.state == State.ENDED:
            st.rerun()
