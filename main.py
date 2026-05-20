"""
Voice Support Copilot - Main Application
This script brings together the LLM, Voice, and RAG engines to create 
a helpful support assistant that can listen, think, and speak.
"""
import asyncio
import os
from engine_arc.llm_engine import LLMEngine
from engine_arc.voice_engine import VoiceEngine
from engine_arc.rag_engine import RAGEngine
from prompt.prompt import SYSTEM_PROMPT

# Set the path to the directory containing support documents
KNOWLEDGE_BASE_DIR = "knowledgebase"

class SupportCopilot:

    def __init__(self):
        """
        Sets up each functional unit and prepares the initial system persona.
        """
        self.llm = LLMEngine()
        self.voice = VoiceEngine(model_path="/opt/vosk-model-en", voice="en-IN-NeerjaNeural")
        self.rag = RAGEngine()
        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    async def handle_interaction(self, user_input, audio_input=None):
        """
        Handles a single turn of conversation, whether it's via voice or text.
        It finds relevant documents, asks the AI for a reply, and then speaks the answer.
        """
        if audio_input:
            text = self.voice.speech_to_text(audio_input)
            print(f"User (Voice): {text}")
        else:
            text = user_input
            print(f"User: {text}")

        context = self.rag.query(text)
        
        augmented_input = f"Context:\n{context}\n\nUser Question: {text}"
        self.history.append({"role": "user", "content": augmented_input})

        response = self.llm.generate_response(self.history)
        self.history.append({"role": "assistant", "content": response})
        print(f"AI: {response}")
        audio_file = await self.voice.text_to_speech(response)
        print(f"Response saved to {audio_file}")
        
        return response, audio_file

    def generate_ticket(self):
        """
        Analyzes the full conversation and creates a brief support ticket summary.
        """
        conv_str = "\n".join([f"{m['role']}: {m['content']}" for m in self.history if m['role'] != 'system'])
        ticket = self.llm.generate_support_summary(conv_str)
        return ticket

async def main():
    """
    The main app loop. It handles document loading and the interaction menu.
    """
    copilot = SupportCopilot()
    
    # We load our knowledge base from the specified directory.
    if os.path.exists(KNOWLEDGE_BASE_DIR):
        files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith(('.pdf', '.txt'))]
        for f in files:
            file_path = os.path.join(KNOWLEDGE_BASE_DIR, f)
            copilot.rag.add_document(file_path)
            print(f"Successfully loaded '{f}' into knowledge memory.")
    else:
        print(f"Warning: Knowledge base directory '{KNOWLEDGE_BASE_DIR}' not found.")

    print("Welcome to Voice Support Copilot.")
    print("Commands: 'v' for voice, 'exit' to end, or just type your question.")
    
    while True:
        user_input = input("\n[Text / 'v' for voice / 'exit'] > ").strip()
        
        if user_input.lower() == 'exit':
            break
        
        if user_input.lower() == 'v':
            # This triggers the live microphone mode.
            text = copilot.voice.live_listen("I am listening... go ahead!")
            if text:
                print(f"I heard: {text}")
                await copilot.handle_interaction(text)
            else:
                print("I couldn't catch that. Could you try again?")
        else:
            # Standard text interaction.
            if user_input:
                await copilot.handle_interaction(user_input)

    print("\nWrapping up... generating your support ticket now.")
    ticket = copilot.generate_ticket()
    print("SUPPORT Ticket")
    print(ticket)

if __name__ == "__main__":
    # Start the event loop and launch the app.
    asyncio.run(main())
