"""
This module manages the core AI brain of our support assistant.
It uses the Qwen model via HF Inference API and includes a ContextWindowManager
for sliding-window history management with automatic summarization.
"""
import os
from collections import deque
from huggingface_hub import InferenceClient
from config import Config
from prompt.prompt import TICKET_SUMMARY_PROMPT


class LLMEngine:
    """
    The orchestrator for our Large Language Model (LLM) interactions.
    Uses the Hugging Face Inference API for serverless generation.
    """
    def __init__(self):
        """
        Initializes the InferenceClient using Config values.
        """
        self.hf_token = Config.HF_TOKEN
        self.model_id = Config.LLM_MODEL_ID
        self.client = InferenceClient(model=self.model_id, token=self.hf_token)

    def generate_response(self, messages, max_new_tokens=None):
        """
        Sends the conversation history (list of message dicts) to HF servers
        and returns the response string.
        """
        if max_new_tokens is None:
            max_new_tokens = Config.LLM_MAX_NEW_TOKENS
        try:
            completion = self.client.chat.completions.create(
                messages=messages,
                max_tokens=max_new_tokens,
                temperature=Config.LLM_TEMPERATURE,
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"LLM Error: {str(e)}"

    def generate(self, prompt: str, max_new_tokens: int = 300) -> str:
        """
        Simple single-prompt generation helper.
        Wraps the prompt in a user message and returns the raw text.
        Used by TicketFlowManager, query expansion, and context compression.
        """
        messages = [{"role": "user", "content": prompt}]
        return self.generate_response(messages, max_new_tokens=max_new_tokens)

    def generate_support_summary(self, conversation_history: str) -> str:
        """
        Creates a structured JSON support ticket by summarizing the conversation.
        """
        summary_messages = [
            {"role": "system", "content": TICKET_SUMMARY_PROMPT.format(conversation=conversation_history)},
            {"role": "user", "content": "Generate the support ticket JSON now."}
        ]
        return self.generate_response(summary_messages, max_new_tokens=400)


class ContextWindowManager:
    """
    Manages conversation history within a token budget.
    Uses a sliding window with summarization when approaching the limit.
    """
    def __init__(self, llm_engine: LLMEngine):
        self.llm = llm_engine
        self.messages: deque = deque()
        self.summary: str = ""
        self._token_count = 0
        self.max_tokens = Config.CONTEXT_MAX_TOKENS
        self.summarize_threshold = Config.CONTEXT_SUMMARIZE_THRESHOLD

    def add(self, role: str, content: str):
        """Add a message and trigger compression if needed."""
        tokens = self._estimate_tokens(content)
        self.messages.append({"role": role, "content": content, "tokens": tokens})
        self._token_count += tokens

        if self._token_count > self.summarize_threshold:
            self._compress()

    def get_history_string(self) -> str:
        """Return the full history as a readable string."""
        lines = []
        if self.summary:
            lines.append(f"[Earlier summary]: {self.summary}")
        for m in self.messages:
            prefix = "User" if m["role"] == "user" else "Alex"
            lines.append(f"{prefix}: {m['content']}")
        return "\n".join(lines)

    def _compress(self):
        """Summarize oldest half of conversation and remove from deque."""
        half = len(self.messages) // 2
        if half == 0:
            return
        to_summarize = [self.messages.popleft() for _ in range(half)]
        self._token_count = sum(m["tokens"] for m in self.messages)

        convo_text = "\n".join(
            f"{'User' if m['role']=='user' else 'Alex'}: {m['content']}"
            for m in to_summarize
        )
        self.summary = self.llm.generate(
            f"Summarize this support conversation in 2 sentences:\n{convo_text}",
            max_new_tokens=100
        )

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate: 1 token ≈ 4 characters."""
        return len(text) // 4
