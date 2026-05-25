# engine_arc/ticket_flow.py
from datetime import datetime
from engine_arc.ticket_engine import SupportTicket

TICKET_QUESTIONS = [
    {
        "field": "user_name",
        "question": "Sure, I'd love to help! To get started, could you share your name with me?",
    },
    {
        "field": "user_email",
        "question": "Thanks! And what's the best email address we can use to follow up with you?",
    },
    {
        "field": "description",
        "question": "Got it. Can you tell me exactly what's happening? Feel free to describe any steps you took and what you expected to see.",
    },
    {
        "field": "priority",
        "question": "Almost done! On a scale of low, medium, high, or critical — how urgent would you say this is for you?",
    },
]

class TicketFlowManager:
    """Manages the step-by-step ticket creation conversation."""

    def __init__(self, llm_engine):
        self.llm = llm_engine
        self.ticket = SupportTicket()
        self.current_step = 0
        self.active = False

    def start(self) -> str:
        self.active = True
        self.current_step = 0
        self.ticket = SupportTicket()
        self.ticket.ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.ticket.created_at = datetime.now().isoformat()
        return (
            "Of course! I'm happy to log a support ticket for you. "
            "I just need a few quick details — it'll only take a minute.\n\n"
            + TICKET_QUESTIONS[0]["question"]
        )

    def next(self, user_input: str) -> tuple[str, bool]:
        """
        Returns (next_message, is_complete).
        Supports conversational fillers and basic corrections.
        """
        raw = user_input.strip()
        q = TICKET_QUESTIONS[self.current_step]

        # 1. Check for corrections of PREVIOUS fields
        if self.current_step > 0:
            previous_q = TICKET_QUESTIONS[self.current_step - 1]
            correction = self._check_for_correction(previous_q["field"], raw)
            if correction:
                setattr(self.ticket, previous_q["field"], correction)
                return f"Oh, I've got it! I've updated your {previous_q['field'].replace('user_', '')} to '{correction}'.\n\nReturning to where we were... {q['question']}", False

        # 2. Extract current field
        if q["field"] in ["user_name", "user_email"]:
            extracted = self._extract_field(q["field"], raw)
        elif q["field"] == "priority":
            extracted = self._normalize_priority(raw)
        else:
            extracted = raw

        # 3. Handle conversational fillers (e.g., "sure", "yes") without actual data
        if extracted in ["MISSING", "AFFIRMATIVE_ONLY"]:
            return f"No problem at all! Just let me know your {q['field'].replace('user_', '')} when you're ready.", False

        setattr(self.ticket, q["field"], extracted)

        # 4. Advance
        self.current_step += 1
        if self.current_step >= len(TICKET_QUESTIONS):
            return self._finalize(), True

        next_q = TICKET_QUESTIONS[self.current_step]
        acks = {
            "user_name": f"Nice to meet you, {extracted}!",
            "user_email": "Perfect, I've got your email.",
            "description": "Thanks for explaining that clearly.",
        }
        ack = acks.get(q["field"], "Got it.")
        return f"{ack}\n\n{next_q['question']}", False

    def _extract_field(self, field: str, raw: str) -> str:
        """Use LLM to clean/normalize specific short fields, detecting placeholders."""
        prompt = (
            f"The user was asked for their {field}. They responded with: '{raw}'.\n"
            f"Rules:\n"
            f"1. If they provided the {field}, return ONLY the clean value (e.g., 'Aditya' or 'test@example.com').\n"
            f"2. If they only said something like 'sure', 'yes', 'ok', or 'go ahead' without providing the string, return 'AFFIRMATIVE_ONLY'.\n"
            f"3. If the response is nonsense or empty relative to the {field}, return 'MISSING'.\n"
            f"Return ONLY one of the results above. No preamble."
        )
        return self.llm.generate(prompt, max_new_tokens=40).strip()

    def _check_for_correction(self, field: str, raw: str) -> str:
        """Heuristic or LLM-based check if user is trying to correct the previous field."""
        if "name" in raw.lower() and field == "user_name" and ("actually" in raw.lower() or "my name is" in raw.lower() or "bad" in raw.lower()):
            return self._extract_field(field, raw)
        # Add email correction logic if needed
        return None

    def _normalize_priority(self, raw: str) -> str:
        """Map user input to a valid priority level."""
        raw_lower = raw.lower()
        for level in ["critical", "high", "medium", "low"]:
            if level in raw_lower:
                return level.upper()
        return "MEDIUM"

    def _finalize(self) -> str:
        self.active = False
        # Only return a short friendly message — NOT the full ticket markdown
        return (
            f"You're all set! 🎉 I've logged your ticket **{self.ticket.ticket_id}** "
            f"and it's been marked as **{self.ticket.priority}** priority.\n\n"
            "Our support team will be in touch at the email you provided. "
            "You can click **'Generate Support Ticket'** below to view the full details anytime."
        )
