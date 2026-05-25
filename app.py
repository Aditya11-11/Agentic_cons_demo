import gradio as gr
import asyncio
import os
import re
from engine_arc.llm_engine import LLMEngine, ContextWindowManager
from engine_arc.voice_engine import VoiceEngine
from engine_arc.rag_engine import RAGEngine, retrieve_with_expansion
from engine_arc.ticket_flow import TicketFlowManager
from prompt.prompt import SYSTEM_PROMPT, INTENT_CLASSIFIER_PROMPT, TICKET_SUMMARY_PROMPT
from config import Config

# ─── Persistent Knowledge Base ───────────────────────────────────────
# On Hugging Face Spaces, the knowledgebase/ folder ships with the repo.
# ChromaDB persists to /data/chroma_db (HF persistent storage).
KNOWLEDGE_BASE_DIR = Config.KNOWLEDGEBASE_DIR
CHROMA_DIR = Config.CHROMA_PERSIST_DIR

# Initialize engines
llm = LLMEngine()
voice = VoiceEngine(model_path=Config.VOSK_MODEL_PATH, voice=Config.TTS_VOICE)
rag = RAGEngine(persist_directory=CHROMA_DIR)
context_manager = ContextWindowManager(llm)
ticket_flow = TicketFlowManager(llm)
active_ticket = None
ticket_offered = False  # Tracks if Alex suggested logging a ticket last turn


def load_kb():
    """Load all documents from the persistent knowledgebase directory."""
    if os.path.exists(KNOWLEDGE_BASE_DIR):
        files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith(('.pdf', '.txt'))]
        for f in files:
            file_path = os.path.join(KNOWLEDGE_BASE_DIR, f)
            rag.add_document(file_path)
            print(f"  ✓ Loaded '{f}' into knowledge memory.")
        return f"Knowledge base loaded: {len(files)} document(s)."
    else:
        print(f"  ⚠ Knowledge base directory '{KNOWLEDGE_BASE_DIR}' not found.")
        return "No knowledge base found."

load_kb()


def respond(user_input: str) -> str:
    """Core response logic matching main.py's SupportCopilot.respond()."""
    global active_ticket, ticket_offered

    # If mid-ticket flow, continue
    if ticket_flow.active:
        response, done = ticket_flow.next(user_input)
        if done:
            active_ticket = ticket_flow.ticket
        context_manager.add("user", user_input)
        context_manager.add("assistant", response)
        return response

    # If Alex offered a ticket last turn and user agreed, start the flow
    _affirmatives = {"sure", "yes", "ok", "okay", "please", "go ahead", "yeah",
                     "yep", "yup", "absolutely", "of course", "do it", "proceed"}
    if ticket_offered and any(a in user_input.lower() for a in _affirmatives):
        ticket_offered = False
        return ticket_flow.start()

    # Classify intent
    intent_prompt = INTENT_CLASSIFIER_PROMPT.format(message=user_input)
    intent = llm.generate(intent_prompt, max_new_tokens=10).strip().lower()

    if intent == "ticket_request":
        ticket_offered = False
        return ticket_flow.start()

    # Only use the hardcoded telephonic intro if it's the very first interaction
    if intent == "greeting":
        ticket_offered = False
        if not context_manager.messages:
            return (
                "Hi there! Thanks for calling PayGate Pro Support. 😊 "
                "My name is Neha, and I'm here to help you today. "
                "What can I assist you with?"
            )
        else:
            return "Hi there! How can I help you further?"

    # RAG retrieval with query expansion
    context = retrieve_with_expansion(user_input, rag.collection, llm)

    # Build prompt with history + context
    history = context_manager.get_history_string()
    system_prompt = SYSTEM_PROMPT.format(context=context, history=history)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    response = llm.generate_response(messages)

    # Check if Alex's response suggests logging a ticket — auto-enable ticket offer flag
    _ticket_keywords = ["log a ticket", "raise a ticket", "create a ticket",
                        "file a ticket", "escalate", "our team can follow up",
                        "support team", "would you like me to log"]
    ticket_offered = any(kw in response.lower() for kw in _ticket_keywords)

    # Update context memory
    context_manager.add("user", user_input)
    context_manager.add("assistant", response)

    return response


def clean_for_tts(text: str) -> str:
    """Clean response text for TTS output: remove <think> tags and all markdown symbols."""
    # Remove thought process
    clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Remove markdown chars: **, _, #, `, etc.
    clean = re.sub(r'[*_#`~>\[\]\(\)]', '', clean)
    # Normalize whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


async def process_voice(audio_path, state):
    """Handle voice input from the Gradio audio component."""
    if not audio_path:
        return state, None, "Please record audio."

    # Transcribe
    text = voice.speech_to_text(audio_path)
    if not text:
        return state, None, "Could not transcribe audio. Please try again."

    # Get response
    response_text = respond(text)
    clean_response = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()

    # Generate TTS audio
    tts_text = clean_for_tts(response_text)
    audio_out = await voice.text_to_speech(tts_text) if tts_text else None

    state.append({"role": "user", "content": text})
    state.append({"role": "assistant", "content": clean_response})

    return state, audio_out, ""


async def process_text(user_input, state):
    """Handle text input from the Gradio textbox."""
    if not user_input:
        return state, None, "", ""

    # Get response
    response_text = respond(user_input)
    clean_response = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()

    # Generate TTS audio
    tts_text = clean_for_tts(response_text)
    audio_out = await voice.text_to_speech(tts_text) if tts_text else None

    state.append({"role": "user", "content": user_input})
    state.append({"role": "assistant", "content": clean_response})

    return state, audio_out, ""


def generate_ticket():
    """Generate a support ticket from the conversation so far."""
    global active_ticket
    if active_ticket:
        return active_ticket.to_markdown()

    history = context_manager.get_history_string()
    if history:
        prompt = TICKET_SUMMARY_PROMPT.format(conversation=history)
        return llm.generate(prompt, max_new_tokens=400)
    return "No conversation to summarize."


# ─── Gradio UI ────────────────────────────────────────────────────────
with gr.Blocks() as demo:
    gr.Markdown("# 🎧 Voice Support Copilot")
    gr.Markdown("Speak or type to **Alex**, your AI support assistant. Powered by TechFlow knowledge base.")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🎙️ Voice")
            audio_input = gr.Audio(label="Speak Here", type="filepath", sources=["microphone"])
            submit_btn = gr.Button("Send Voice Message", variant="primary")

            gr.Markdown("---")
            gr.Markdown("### ⌨️ Text")
            text_input = gr.Textbox(label="Type your message", placeholder="How do I reset my password?")
            text_btn = gr.Button("Send Text Message")

            status_msg = gr.Markdown("")

        with gr.Column(scale=2):
            chatbot = gr.Chatbot(label="Conversation")
            audio_output = gr.Audio(label="AI Voice Response", autoplay=True)

    with gr.Row():
        ticket_btn = gr.Button("📋 Generate Support Ticket")
        ticket_output = gr.Textbox(label="Support Ticket Summary", lines=8)

    state = gr.State([])

    submit_btn.click(
        process_voice,
        inputs=[audio_input, state],
        outputs=[chatbot, audio_output, status_msg]
    )

    text_btn.click(
        process_text,
        inputs=[text_input, state],
        outputs=[chatbot, audio_output, status_msg]
    )

    text_input.submit(
        process_text,
        inputs=[text_input, state],
        outputs=[chatbot, audio_output, status_msg]
    )

    ticket_btn.click(
        generate_ticket,
        outputs=[ticket_output]
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft(), share=True)
