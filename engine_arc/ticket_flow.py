# engine_arc/ticket_flow.py
from datetime import datetime
from engine_arc.ticket_engine import SupportTicket

TICKET_QUESTIONS = [
    {
        "field": "user_name",
        "question": "Let's get started! Could I get your name please?",
        "follow_up": None,
    },
    {
        "field": "user_email",
        "question": "And what's the best email address to reach you at?",
        "follow_up": None,
    },
    {
        "field": "subject",
        "question": "Great! In one short sentence — what's the main issue you're experiencing?",
        "follow_up": None,
    },
    {
        "field": "description",
        "question": "Can you describe the problem in a bit more detail? What exactly is happening?",
        "follow_up": "Is there anything else about the issue you'd like to add?",
    },
    {
        "field": "steps_to_reproduce",
        "question": "What steps did you take right before the problem occurred?",
        "follow_up": None,
    },
    {
        "field": "expected_behavior",
        "question": "What did you expect to happen?",
        "follow_up": None,
    },
    {
        "field": "actual_behavior",
        "question": "And what actually happened instead?",
        "follow_up": None,
    },
    {
        "field": "priority",
        "question": "How urgent is this for you? (low / medium / high / critical)",
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
            "I'd be happy to help you log a support ticket! "
            "I'll ask you a few quick questions.\n\n"
            + TICKET_QUESTIONS[0]["question"]
        )

    def next(self, user_input: str) -> tuple[str, bool]:
        """
        Returns (next_message, is_complete).
        Feed user_input for current question, advance to next.
        """
        q = TICKET_QUESTIONS[self.current_step]
        # Use LLM to extract clean value from user's natural-language response
        extracted = self._extract_field(q["field"], user_input)
        setattr(self.ticket, q["field"], extracted)

        self.current_step += 1
        if self.current_step >= len(TICKET_QUESTIONS):
            return self._finalize(), True

        next_q = TICKET_QUESTIONS[self.current_step]
        confirmation = f"Got it — *{extracted}*.\n\n{next_q['question']}"
        return confirmation, False

    def _extract_field(self, field: str, raw: str) -> str:
        """Use LLM to clean/normalize the user's answer."""
        prompt = (
            f"Extract the value for '{field}' from this user response: '{raw}'. "
            f"Return ONLY the clean value, no extra commentary."
        )
        return self.llm.generate(prompt, max_new_tokens=60).strip()

    def _finalize(self) -> str:
        self.active = False
        return (
            f"Perfect! I've logged your ticket **{self.ticket.ticket_id}**.\n\n"
            + self.ticket.to_markdown()
        )
