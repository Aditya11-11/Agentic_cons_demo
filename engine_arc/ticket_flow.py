# engine_arc/ticket_flow.py
from datetime import datetime
from engine_arc.ticket_engine import SupportTicket

TICKET_QUESTIONS = [
    {
        "field": "user_name",
        "question": "Sure, I'd love to help! To get started, could you share your name with me?",
        "follow_up": None,
    },
    {
        "field": "user_email",
        "question": "Thanks! And what's the best email address we can use to follow up with you?",
        "follow_up": None,
    },
    {
        "field": "subject",
        "question": "Got it! In just a few words, what's the issue you're running into?",
        "follow_up": None,
    },
    {
        "field": "description",
        "question": "I see. Can you tell me a little more about what's happening? Any details you can share would be really helpful.",
        "follow_up": "Is there anything else about the issue you'd like me to note?",
    },
    {
        "field": "steps_to_reproduce",
        "question": "Understood. Walk me through what you were doing just before this happened — what steps did you take?",
        "follow_up": None,
    },
    {
        "field": "expected_behavior",
        "question": "And what were you hoping or expecting would happen at that point?",
        "follow_up": None,
    },
    {
        "field": "actual_behavior",
        "question": "I see — so what actually happened instead? What did you see on your screen?",
        "follow_up": None,
    },
    {
        "field": "priority",
        "question": "Almost done! On a scale of low, medium, high, or critical — how urgent would you say this is for you?",
        "follow_up": None,
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
        # Store the raw user input directly — don't mangle it with LLM extraction
        raw = user_input.strip()
        if q["field"] == "priority":
            extracted = self._normalize_priority(raw)
        else:
            extracted = raw
        setattr(self.ticket, q["field"], extracted)

        self.current_step += 1
        if self.current_step >= len(TICKET_QUESTIONS):
            return self._finalize(), True

        next_q = TICKET_QUESTIONS[self.current_step]
        # Natural acknowledgement without echoing the full input back
        acks = {
            "user_name": f"Nice to meet you, {extracted}!",
            "user_email": "Perfect, I've got your email.",
            "subject": "Got it.",
            "description": "Thanks for explaining that.",
            "steps_to_reproduce": "That's helpful, thank you.",
            "expected_behavior": "Makes sense.",
            "actual_behavior": "I understand, that sounds frustrating.",
        }
        ack = acks.get(q["field"], "Got it.")
        return f"{ack}\n\n{next_q['question']}", False

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
