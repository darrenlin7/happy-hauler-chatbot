"""
app.py — Streamlit entry point for the Happy Hauler recruiting chatbot.

Run with:
    streamlit run app.py

Ties together:
  - ConversationStateMachine  (flow control — no LLM)
  - llm.*                     (interpretation, FAQ answers, summary)
  - database.*                (SQLite persistence)
"""

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

# ─── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Happy Hauler — Recruiting Assistant",
    page_icon="🚛",
    layout="centered",
)

# ─── One-time DB setup ────────────────────────────────────────────────────────
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

# Maps each state to the fixed question the bot asks on entry
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

# Ordered follow-up prompts for the experience question
_EXPERIENCE_FOLLOWUPS = [
    "Could you give me an exact number of years? For example, '3 years' or '5 years'.",
    (
        "I need a specific number to move forward — how many years have you been "
        "driving a commercial truck?"
    ),
]


# ─── Session state helpers ────────────────────────────────────────────────────

def _init_session() -> None:
    """Initialize all session_state keys on first page load."""
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
    """Append a bot message to history and render it immediately."""
    _add_message("assistant", text)
    with st.chat_message("assistant"):
        st.write(text)


# ─── Screening prompt picker ──────────────────────────────────────────────────

def _screening_prompt(sm: ConversationStateMachine) -> str:
    """
    Return the appropriate bot prompt for the current state.
    All screening question strings are hardcoded here — no LLM call needed.
    """
    state = sm.state

    if state == State.GREETING:
        return _GREETING_REPROMPT  # Only reached if user wasn't ready

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


# ─── Main App ─────────────────────────────────────────────────────────────────

def main() -> None:
    _init_session()

    sm: ConversationStateMachine = st.session_state.sm

    st.title("🚛 Happy Hauler Recruiting Assistant")

    # Show initial greeting on the very first page load
    if not st.session_state.messages:
        _add_message("assistant", _INITIAL_GREETING)

    # Render the full message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # ── End-of-conversation UI ────────────────────────────────────────────────
    if sm.state == State.ENDED:
        if not st.session_state.saved:
            # Generate summary and persist the session exactly once
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

        st.divider()
        if sm.passed:
            st.success("✅  **PASSED** — Candidate meets initial qualifications.")
        else:
            st.error("❌  **FAILED** — Candidate does not meet minimum requirements.")

        with st.expander("Session Summary", expanded=True):
            st.write(st.session_state.get("summary", ""))

        if st.button("Start New Conversation", type="primary"):
            for key in ("sm", "messages", "session_id", "saved", "summary"):
                st.session_state.pop(key, None)
            st.rerun()
        return  # No chat input after the conversation ends

    # ── Chat input ────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Type your response here…"):
        # Render user message
        _add_message("user", prompt)
        with st.chat_message("user"):
            st.write(prompt)

        prev_state = sm.state

        # Step 1: LLM classifies the candidate's intent
        interpretation = interpret_response(prev_state, prompt)
        intent = interpretation.get("intent", "vague")
        extracted_value = interpretation.get("extracted_value")

        # Step 2: Handle QA_OPEN specially — questions get answered in-state
        if prev_state == State.QA_OPEN:
            if intent == "question":
                # Answer the question using FAQ-grounded LLM call
                answer = answer_faq_question(
                    prompt, st.session_state.messages[:-1]
                )
                _bot(answer)
                _bot("Is there anything else you'd like to know, or are you all set?")
                st.stop()

            if intent == "yes":
                # Candidate said "yes" (has more questions) but hasn't asked yet
                _bot("Sure! What would you like to know?")
                st.stop()

            # intent == "no" or "vague" → fall through to sm.process below
            # which will transition to ENDED (pass)

        # Step 3: State machine decides the transition
        sm.process(intent, extracted_value)

        # Step 4: Generate and display the bot's response for the new state
        response = _screening_prompt(sm)
        if response:
            _bot(response)

        # Step 5: If we just ended, rerun to show the pass/fail badge
        if sm.state == State.ENDED:
            st.rerun()


main()
