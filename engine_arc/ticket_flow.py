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
        Feed user_input for current question, advance to next.
        """
        q = TICKET_QUESTIONS[self.current_step]
        raw = user_input.strip()

        # Conditional extraction logic
        if q["field"] in ["user_name", "user_email"]:
            extracted = self._extract_field(q["field"], raw)
        elif q["field"] == "priority":
            extracted = self._normalize_priority(raw)
        else:
            extracted = raw

        setattr(self.ticket, q["field"], extracted)

        self.current_step += 1
        if self.current_step >= len(TICKET_QUESTIONS):
            return self._finalize(), True

        next_q = TICKET_QUESTIONS[self.current_step]
        # Natural acknowledgement
        acks = {
            "user_name": f"Nice to meet you, {extracted}!",
            "user_email": "Perfect, I've got your email.",
            "description": "Thanks for explaining that clearly.",
        }
        ack = acks.get(q["field"], "Got it.")
        return f"{ack}\n\n{next_q['question']}", False

    def _extract_field(self, field: str, raw: str) -> str:
        """Use LLM to clean/normalize specific short fields like name or email."""
        prompt = (
            f"The user was asked for their '{field}'. They responded with: '{raw}'.\n"
            f"If the response contains a {field}, return ONLY that clean value.\n"
            f"If it's just nonsense or metadata, try to extract the core {field}.\n"
            f"Return ONLY the value. No preamble."
        )
        return self.llm.generate(prompt, max_new_tokens=40).strip()

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
