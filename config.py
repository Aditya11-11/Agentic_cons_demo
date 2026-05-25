# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM
    LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")
    LLM_MAX_NEW_TOKENS = int(os.getenv("LLM_MAX_NEW_TOKENS", 300))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.7))
    LLM_DEVICE = os.getenv("LLM_DEVICE", "auto")  # auto, cpu, cuda
    HF_TOKEN = os.getenv("HF_TOKEN")

    # Context Window
    CONTEXT_MAX_TOKENS = int(os.getenv("CONTEXT_MAX_TOKENS", 1800))
    CONTEXT_SUMMARIZE_THRESHOLD = int(os.getenv("CONTEXT_SUMMARIZE_THRESHOLD", 1400))

    # RAG
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_store")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", 400))
    RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", 80))
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", 5))
    KNOWLEDGEBASE_DIR = os.getenv("KNOWLEDGEBASE_DIR", "./knowledgebase")

    # Voice
    VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "/opt/vosk-model-en")
    TTS_VOICE = os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")

    # Tickets
    TICKET_OUTPUT_DIR = os.getenv("TICKET_OUTPUT_DIR", "./tickets")
