"""
Voice Support Copilot - Main Application (Improved)
Integrates LLM, Voice, RAG engines with intent classification,
conversational ticket creation, and context window management.
"""
import asyncio
import os
import re
from engine_arc.llm_engine import LLMEngine, ContextWindowManager
from engine_arc.voice_engine import VoiceEngine
from engine_arc.rag_engine import RAGEngine, retrieve_with_expansion
from engine_arc.ticket_flow import TicketFlowManager
from prompt.prompt import SYSTEM_PROMPT, INTENT_CLASSIFIER_PROMPT, TICKET_SUMMARY_PROMPT
from config import Config


class SupportCopilot:
    """
    Main orchestrator that ties together voice, LLM, RAG, ticketing,
    and context management into a coherent support experience.
    """

    def __init__(self):
        self.llm = LLMEngine()
        self.voice = VoiceEngine(
            model_path=Config.VOSK_MODEL_PATH,
            voice=Config.TTS_VOICE
        )
        self.rag = RAGEngine()
        self.context_manager = ContextWindowManager(self.llm)
        self.ticket_flow = TicketFlowManager(self.llm)
        self.active_ticket = None

    def classify_intent(self, user_input: str) -> str:
        """Use the LLM to classify the user's intent."""
        prompt = INTENT_CLASSIFIER_PROMPT.format(message=user_input)
        return self.llm.generate(prompt, max_new_tokens=10).strip().lower()

    def respond(self, user_input: str) -> str:
        """
        Core response logic. Handles ticket flow, intent classification,
        RAG retrieval, and LLM generation with context management.
        """
        # If we're mid-ticket-creation, continue that flow
        if self.ticket_flow.active:
            response, done = self.ticket_flow.next(user_input)
            if done:
                self.active_ticket = self.ticket_flow.ticket
            self.context_manager.add("user", user_input)
            self.context_manager.add("assistant", response)
            return response

        # Classify intent
        intent = self.classify_intent(user_input)

        if intent == "ticket_request":
            return self.ticket_flow.start()

        # Retrieve RAG context (with query expansion)
        context = retrieve_with_expansion(
            user_input, self.rag.collection, self.llm
        )

        # Build prompt with history + context
        history = self.context_manager.get_history_string()
        system_prompt = SYSTEM_PROMPT.format(context=context, history=history)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        response = self.llm.generate_response(messages)

        # Update memory
        self.context_manager.add("user", user_input)
        self.context_manager.add("assistant", response)

        return response

    def _clean_for_tts(self, text: str) -> str:
        """Clean response text for TTS output."""
        # Remove <think> tags content
        clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Strip non-ASCII (emojis etc.)
        clean = clean.encode('ascii', 'ignore').decode('ascii').strip()
        return clean

    async def handle_interaction(self, user_input: str):
        """
        Handles a single turn: generates a response, prints it,
        and optionally speaks it via TTS.
        """
        response = self.respond(user_input)
        print(f"Alex: {response}\n")

        # Generate audio from cleaned response
        clean_text = self._clean_for_tts(response)
        if clean_text:
            audio_file = await self.voice.text_to_speech(clean_text)
            print(f"  [Audio saved to {audio_file}]")

        return response

    def _on_exit(self):
        """Generate or display the final support ticket on exit."""
        if self.active_ticket:
            print("\n--- Your Support Ticket ---")
            print(self.active_ticket.to_markdown())
        else:
            # Auto-generate ticket from conversation history
            history = self.context_manager.get_history_string()
            if history:
                prompt = TICKET_SUMMARY_PROMPT.format(conversation=history)
                raw_json = self.llm.generate(prompt, max_new_tokens=400)
                print("\n--- Auto-Generated Ticket Summary ---")
                print(raw_json)
            else:
                print("\nNo conversation to summarize. Goodbye!")


async def main():
    """The main app loop. Handles document loading and the interaction menu."""
    copilot = SupportCopilot()

    # Load knowledge base
    kb_dir = Config.KNOWLEDGEBASE_DIR
    if os.path.exists(kb_dir):
        files = [f for f in os.listdir(kb_dir) if f.endswith(('.pdf', '.txt'))]
        for f in files:
            file_path = os.path.join(kb_dir, f)
            copilot.rag.add_document(file_path)
            print(f"  Loaded '{f}' into knowledge memory.")
    else:
        print(f"  Warning: Knowledge base directory '{kb_dir}' not found.")

    # Ensure ticket output directory exists
    os.makedirs(Config.TICKET_OUTPUT_DIR, exist_ok=True)

    print("\n" + "=" * 60)
    print("  Alex: Hi! I'm Alex, your support assistant.")
    print("  How can I help you today?")
    print("=" * 60)
    print("Commands: type your question | 'v' = voice | 'ticket' = log issue | 'exit' = quit\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() == "exit":
            copilot._on_exit()
            break
        if user_input.lower() == "v":
            text = copilot.voice.live_listen("I am listening... go ahead!")
            if text:
                print(f"You (voice): {text}")
                await copilot.handle_interaction(text)
            else:
                print("I couldn't catch that. Could you try again?")
            continue
        if user_input.lower() == "ticket":
            user_input = "I want to log a support ticket"

        await copilot.handle_interaction(user_input)


if __name__ == "__main__":
    asyncio.run(main())

