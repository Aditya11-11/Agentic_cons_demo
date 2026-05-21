"""
This module manages the core AI brain of our support assistant.
It uses the Qwen3 model to handle conversations and generate structured summaries.
"""
import os
from huggingface_hub import InferenceClient
from prompt.prompt import SUMMARY_PROMPT

class LLMEngine:
    """
    The orchestrator for our Large Language Model (LLM) interactions.
    Now uses the Hugging Face Inference API for blazing-fast serverless generation.
    """
    def __init__(self):
        """
        Initializes the InferenceClient using the HF_TOKEN from environment variables.
        """
        self.hf_token = os.environ.get("HF_TOKEN")
        self.model_id = "Qwen/Qwen2.5-7B-Instruct"
        self.client = InferenceClient(model=self.model_id, token=self.hf_token)

    def generate_response(self, messages, max_new_tokens=512):
        """
        Sends the conversation history to HF servers and returns the response.
        """
        try:
            completion = self.client.chat.completions.create(
                messages=messages,
                max_tokens=max_new_tokens,
                temperature=0.7,
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"LLM Error: {str(e)}"

    def generate_support_summary(self, conversation_history):
        """
        Creates a structured support ticket by summarizing the conversation.
        """
        summary_messages = [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": f"Please summarize this conversation into a support ticket:\n\n{conversation_history}"}
        ]
        return self.generate_response(summary_messages)
