"""
This module manages the core AI brain of our support assistant.
It uses the Qwen3 model to handle conversations and generate structured summaries.
"""
import torch
from transformers import pipeline
from prompt.prompt import SUMMARY_PROMPT

class LLMEngine:
    """
    The orchestrator for our Large Language Model (LLM) interactions.
    It's responsible for loading the model and managing the chat pipeline.
    """
    def __init__(self):
        """
        Sets up the text generation pipeline, choosing between GPU or CPU 
        based on what's available on the system.
        """
        self.model_id = "Qwen/Qwen3-1.7B"
        self.pipe = pipeline(
            "text-generation", 
            model=self.model_id, 
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
        )

    def generate_response(self, messages, max_new_tokens=512):
        """
        Takes a list of past messages and generates the next logical reply 
        from the AI's perspective.
        """
        outputs = self.pipe(messages, max_new_tokens=max_new_tokens)
        return outputs[0]["generated_text"][-1]["content"]

    def generate_support_summary(self, conversation_history):
        """
        Look back at everything discussed and boil it down into a 
        clean, structured support ticket for the team.
        """
        summary_prompt = [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": conversation_history}
        ]
        return self.generate_response(summary_prompt)
