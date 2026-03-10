"""
state_machine.py — Controls conversation flow for the recruiting chatbot.


Design principle: Python logic owns ALL state transitions. The LLM is only
used for natural language interpretation and generation — never flow control.

State flow:
    GREETING → ASKING_CDL → ASKING_EXPERIENCE → ASKING_OVERNIGHT
             → QA_OPEN → ENDED

Early exits:
    No CDL       → ENDED (fail)
    No overnight → ENDED (fail)
"""

from __future__ import annotations

from config import MAX_FOLLOWUP_ATTEMPTS, State


class ConversationStateMachine:
    """
    Tracks the current screening state and enforces all transition rules.

    Usage:
        sm = ConversationStateMachine()
        intent, value = llm.interpret_response(sm.state, user_message)
        sm.process(intent, value)   # mutates sm.state in place
        response = _next_prompt(sm) # use sm.state to pick the right bot text
    """

    def __init__(self) -> None:
        self.state: State = State.GREETING
        # Number of clarification follow-ups issued for the current question
        self.follow_up_count: int = 0
        # Captured data
        self.experience_years: float | None = None
        # Outcome
        self.passed: bool | None = None
        self.fail_reason: str | None = None  # "no_cdl" | "no_overnight" | None

    # ── Public API ────────────────────────────────────────────────────────────

    def process(self, intent: str, extracted_value: str | None) -> State:
        """
        Apply the candidate's interpreted intent to advance (or stay in) the
        current state. Returns the resulting State so callers can react.
        """
        if self.state == State.GREETING:
            self._handle_greeting(intent)
        elif self.state == State.ASKING_CDL:
            self._handle_cdl(intent)
        elif self.state == State.ASKING_EXPERIENCE:
            self._handle_experience(intent, extracted_value)
        elif self.state == State.ASKING_OVERNIGHT:
            self._handle_overnight(intent)
        elif self.state == State.QA_OPEN:
            self._handle_qa_open(intent)
        # ENDED is a terminal state — no transitions out

        return self.state

    @property
    def is_ended(self) -> bool:
        return self.state == State.ENDED

    # ── Per-state handlers ────────────────────────────────────────────────────

    def _handle_greeting(self, intent: str) -> None:
        # Only advance when the candidate clearly agrees to proceed
        if intent == "yes":
            self.state = State.ASKING_CDL
        # "no" and "vague" keep the bot in GREETING to re-prompt

    def _handle_cdl(self, intent: str) -> None:
        if intent == "yes":
            self.state = State.ASKING_EXPERIENCE
        elif intent == "no":
            self._end(passed=False, reason="no_cdl")
        # "vague" stays in ASKING_CDL for another attempt

    def _handle_experience(self, intent: str, extracted_value: str | None) -> None:
        # Only a "yes" with a parseable number counts as a clear answer
        if intent == "yes" and extracted_value is not None:
            try:
                self.experience_years = float(extracted_value)
                self.state = State.ASKING_OVERNIGHT
                self.follow_up_count = 0
                return
            except (ValueError, TypeError):
                pass  # Fall through to vague handling

        # Anything without a clear number triggers a follow-up or skips ahead
        self._handle_followup_or_skip()

    def _handle_overnight(self, intent: str) -> None:
        if intent == "yes":
            self.state = State.QA_OPEN
        elif intent in ("no", "vague"):
            # Treat refusal or non-answer as a disqualifying response
            self._end(passed=False, reason="no_overnight")

    def _handle_qa_open(self, intent: str) -> None:
        # "no" means the candidate has no more questions → end with a pass
        # "question" and "yes" stay in QA_OPEN (handled in app.py)
        if intent == "no":
            self._end(passed=True, reason=None)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _handle_followup_or_skip(self) -> None:
        """
        Either issue another clarification prompt (stay in state) or give up
        and move on after MAX_FOLLOWUP_ATTEMPTS failed attempts.
        """
        if self.follow_up_count < MAX_FOLLOWUP_ATTEMPTS:
            self.follow_up_count += 1  # Stay in current state, increment counter
        else:
            # Max follow-ups exhausted — move on without capturing experience
            self.experience_years = None
            self.follow_up_count = 0
            self.state = State.ASKING_OVERNIGHT

    def _end(self, passed: bool, reason: str | None) -> None:
        self.state = State.ENDED
        self.passed = passed
        self.fail_reason = reason
