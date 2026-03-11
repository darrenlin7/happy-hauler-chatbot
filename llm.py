"""
llm.py — Anthropic Claude API wrapper.

All API calls go through this module. The state machine and UI never import
anthropic directly.

Responsibilities:
  1. interpret_response   — classify candidate intent, return structured JSON
  2. answer_faq_question  — answer a free-form question using company FAQ data
  3. generate_closing     — polite closing line (pass or fail variant)
  4. generate_summary     — short recruiter-facing session summary
"""

from __future__ import annotations

import json
import anthropic
from dotenv import load_dotenv

from config import COMPANY_FAQ, COMPANY_NAME, State

load_dotenv()

_client = anthropic.Anthropic()  # Reads ANTHROPIC_API_KEY from env automatically
MODEL = "claude-haiku-4-5-20251001"


# ─── Internal helper ──────────────────────────────────────────────────────────

def _chat(system: str, messages: list[dict], max_tokens: int = 256) -> str:
    """Make a single API call and return the raw text response."""
    response = _client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return response.content[0].text.strip()


# ─── 1. Intent classification ─────────────────────────────────────────────────

def interpret_response(state: State, user_message: str) -> dict:
    """
    Ask the LLM to classify the candidate's message given the current state.

    Returns a dict:
        {"intent": "yes"|"no"|"vague"|"question", "extracted_value": "3" | null}

    The state_machine.py module uses this dict to make all transition decisions.
    """
    state_context = {
        State.GREETING: (
            "The bot greeted the candidate and asked if they're ready "
            "to answer a few quick screening questions."
        ),
        State.ASKING_CDL: (
            "The bot asked whether the candidate holds a valid Class A CDL."
        ),
        State.ASKING_EXPERIENCE: (
            "The bot asked how many years of commercial truck driving experience "
            "the candidate has. A specific number is required."
        ),
        State.ASKING_OVERNIGHT: (
            "The bot asked if the candidate is comfortable being on the "
            "road 2 nights per week as a regular part of the job."
        ),
        State.QA_OPEN: (
            "The bot asked if the candidate has any questions about the role. "
            "The candidate is either asking a question or signaling they are done."
        ),
    }

    system = """You are a response classifier for a truck driver recruiting chatbot.
Analyze the candidate's message given its context and return ONLY valid JSON — no markdown, no explanation.

Schema:
  intent          "yes" | "no" | "vague" | "question"
  extracted_value  string | null

Intent rules:
  "yes"      — clear affirmative or a specific direct answer to the question asked
  "no"       — clear negative, refusal, or denial
  "vague"    — ambiguous, evasive, off-topic, or unclear
  "question" — the candidate is asking something (only valid in QA_OPEN context)

Special rule for ASKING_EXPERIENCE:
  If the candidate gives a clear number of years (words or digits), set intent
  to "yes" and extracted_value to that number as a digit string (e.g. "3").
  Convert word numbers: "three" → "3", "two" → "2", etc.
  Ranges like "3-5 years" → use the lower bound ("3").
  If no specific number is given, set intent to "vague".

Special rule for QA_OPEN:
  Use "question" when the candidate is asking something specific.
  Use "no" when they indicate they have no more questions or are done."""

    user_content = (
        f"Context: {state_context.get(state, 'General screening question.')}\n\n"
        f'Candidate said: "{user_message}"\n\n'
        "Return JSON only."
    )

    raw = _chat(system, [{"role": "user", "content": user_content}])

    # Strip accidental markdown code fences from the response
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Safe fallback — treat as vague so state machine stays put
        return {"intent": "vague", "extracted_value": None}


# ─── 2. FAQ answering ─────────────────────────────────────────────────────────

def answer_faq_question(question: str, history: list[dict]) -> str:
    """
    Use the LLM to answer a candidate question during QA_OPEN.

    Injects company FAQ into the system prompt so answers are grounded in
    real data rather than hallucinated. `history` provides conversation context.
    """
    system = f"""You are a friendly and professional recruiting assistant for {COMPANY_NAME}.
Answer the candidate's question concisely (1–3 sentences) using the company information below.
If the answer isn't in the provided info, say you're not certain and they can find out more once they speak with the team.

Do not ask follow-up questions in your reply.
Do not offer to connect the candidate with a recruiter or suggest they reach out to anyone.

{COMPANY_FAQ}"""

    # Include recent conversation for context, then append the new question
    recent = [{"role": m["role"], "content": m["content"]} for m in history[-6:]]
    recent.append({"role": "user", "content": question})

    return _chat(system, recent, max_tokens=256)


# ─── 3. Closing message ───────────────────────────────────────────────────────

def generate_closing(passed: bool, fail_reason: str | None = None) -> str:
    """
    Return a short, polite closing message. Hardcoded (no LLM call needed)
    because these messages need to be precise and consistent.
    """
    if not passed:
        if fail_reason == "no_cdl":
            return (
                "This role requires a valid Class A CDL. Thank you for your "
                "time, and best of luck in your job search!"
            )
        if fail_reason == "no_overnight":
            return (
                "Unfortunately, overnight travel is a core part of this role. "
                "Thank you for considering Happy Hauler — best of luck!"
            )
        return "Thank you for your time. Best of luck in your job search!"

    return (
        "Thank you for chatting with us! A recruiter from Happy Hauler Trucking Co. "
        "will be in touch with you shortly."
    )


# ─── 4. Session summary ───────────────────────────────────────────────────────

def generate_summary(
    messages: list[dict],
    passed: bool,
    experience_years: float | None,
) -> str:
    """
    Ask the LLM to write a brief recruiter-facing summary of the session.
    Returns a 2–3 sentence paragraph suitable for the Past Chats page.
    """
    system = """You are summarizing a recruiting chatbot screening session for a Class A CDL truck driver role.
Write a concise 2–3 sentence summary covering: qualifications shared, the final outcome, and any notable details.
Be factual and professional. Do not add opinions or filler."""

    transcript = "\n".join(
        f"{'Assistant' if m['role'] == 'assistant' else 'Candidate'}: {m['content']}"
        for m in messages
    )
    outcome = "PASSED" if passed else "FAILED"
    exp_note = f"{experience_years} years" if experience_years is not None else "not captured clearly"

    user_content = (
        f"Outcome: {outcome}\n"
        f"Experience captured: {exp_note}\n\n"
        f"Transcript:\n{transcript}\n\n"
        "Write the summary now."
    )

    return _chat(system, [{"role": "user", "content": user_content}], max_tokens=256)
