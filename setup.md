# Setup & Usage Guide

Follow these simple steps to get your **Voice Support Copilot** up and running.

## Prerequisites
- **Docker** installed on your machine.
- A **Microphone** (for voice interaction).
- **Internet connection** (for the first build to download the AI models).

---

## 1. Installation

First, clone the repository:
git clone https://github.com/Aditya11-11/Agentic_cons_demo
cd Case_Study
```
### Add Knowledge
Simply place your PDFs or text files into the `knowledgebase/` directory. The assistant will automatically read all files in that folder on startup.

### Option A: Using Docker (Recommended)
Building the container ensures all audio and AI dependencies are correctly configured.
# Build the image
docker build -t support-copilot .

# Run the assistant
docker run -it support-copilot
```

### Option B: Local Setup (Without Docker)
1. **Install PortAudio** (needed for microphone support):
   - Linux: `sudo apt-get install portaudio19-dev`
   - Mac: `brew install portaudio`
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Vosk Model**:
   Download the [Indian English Vosk model](https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip), unzip it, and set the path in `engine_arc/voice_engine.py` or as an environment variable `VOSK_MODEL_PATH`.
4. **Run**:
   ```bash
   python main.py
   ```

---

## 2. Using the Assistant

### Text Mode
Just type your question at any time. The assistant will check the Case Study PDF and reply.

### Voice Mode (Live)
1. Type **`v`** and hit Enter.
2. When you see `I am listening...`, speak clearly.
3. Once you stop talking, the system will process your voice and reply with a neural voice.

### Ending the Session
Type **`exit`** to stop. The system will automatically generate a structured **Support Ticket Summary** of your whole conversation.

---

## 3. Project Structure
- `main.py`: The starting point of the app.
- `engine_arc/`: Contains the Brain (LLM), Voice, and Knowledge (RAG) engines.
- `prompt/prompt.py`: The place to change the assistant's personality or summary format.
- `chroma_db/`: Local folder where document knowledge is stored.

## Troubleshooting
- **No Sound?** If running inside Docker, ensure your environment supports audio passthrough (usually `ALSA` on Linux). 
- **Slow?** The Qwen3-1.7B model runs best on a machine with at least 8GB of RAM.
