# Case Study: Voice Support Copilot

## 1. Technical Overview

### Architecture Decisions
The system follows a modular **Engine-based Architecture**, separating concerns into three primary units orchestrated by a central `SupportCopilot` controller:

*   **LLM Engine**: Utilizes **Qwen/Qwen3-1.7B** via the `transformers` library. This model was chosen for its high performance-to-size ratio, allowing for efficient local inference without sacrificial latency.
*   **Voice Engine**: Implements a hybrid STT/TTS system. 
    *   **STT (Speech-to-Text)**: Uses **Vosk** for local, offline recognition. This ensures low latency and data privacy.
    *   **TTS (Text-to-Speech)**: Uses **edge-tts** for cloud-based, high-quality neural voice synthesis, providing a more natural user experience.
*   **RAG Engine**: Powered by **ChromaDB** with `all-MiniLM-L6-v2` embeddings. It handles document parsing (PDF/TXT) and semantic retrieval to ground AI responses in business-specific context.

### Reasoning
The "Local-First" approach (local LLM and STT) was prioritized to demonstrate **operational efficiency** and **practicality**. By running heavy components locally, the system minimizes API costs and dependency on external services, making it a viable prototype for enterprise support environments.

---

## 2. Assumptions & Tradeoffs

### Assumptions
*   **Environment**: The system is designed for environments where low-latency response times are critical for user engagement.
*   **Hardware**: Assumes a standard workstation with CPU-based inference capability (though GPU is supported and auto-detected).

### Tradeoffs
*   **Model Complexity vs. Speed**: A 1.7B parameter model was selected over larger alternatives (e.g., 7B+) to ensure near-instantaneous responses on standard hardware, compromising slightly on deep reasoning for significantly better UX.
*   **Vosk vs. Whisper**: Vosk was chosen for its ability to handle live microphone streams with minimal CPU overhead, whereas Whisper (while more accurate) often requires significant resources for real-time speech processing.

### Future Improvements
*   **Multi-step Reasoning**: Implementing an Agentic loop (e.g., ReAct) to allow the assistant to perform actions like looking up order statuses or checking inventory.
*   **Fine-tuning**: Fine-tuning the LLM on specific support transcripts to improve industry-specific tone and vocabulary.
*   **Streaming TTS**: Updating the voice engine to stream audio chunks instead of saving to a file first for even lower perceived latency.

---

## 3. Demonstration & Implementation

### Source Code Structure
The codebase is organized as follows:
*   [main.py](file:///home/aditya/nltk_data/Case_Study/main.py): Central orchestration and CLI loop.
*   [engine_arc/](file:///home/aditya/nltk_data/Case_Study/engine_arc):
    *   [llm_engine.py](file:///home/aditya/nltk_data/Case_Study/engine_arc/llm_engine.py): LLM management and pipeline setup.
    *   [rag_engine.py](file:///home/aditya/nltk_data/Case_Study/engine_arc/rag_engine.py): Document ingestion and vector search.
    *   [voice_engine.py](file:///home/aditya/nltk_data/Case_Study/engine_arc/voice_engine.py): STT (Vosk) and TTS (edge-tts) logic.
*   [prompt/](file:///home/aditya/nltk_data/Case_Study/prompt):
    *   [prompt.py](file:///home/aditya/nltk_data/Case_Study/prompt/prompt.py): System instructions and summary structuring.

### Setup Instructions
1.  **Dependencies**: Install required packages:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Voice Model**: Download a Vosk model and place it in `/opt/vosk-model-en`.
3.  **Launch**: Run the application:
    ```bash
    python main.py
    ```

### Walkthrough
1.  **Knowledge Loading**: On startup, the system automatically parses documents in the `knowledgebase/` folder into the vector store.
2.  **Interaction**: The user can type questions or press 'v' to speak.
3.  **Contextual Reply**: The RAG engine retrieves relevant snippets, and the LLM generates a grounded response.
4.  **Ticket Generation**: Upon exit, the system summarizes the entire interaction into a structured support ticket.

---

## 4. Evaluation Criteria Checklist

*   **AI Engineering**: Demonstrated through the integration of RAG, local LLMs, and Voice pipelines.
*   **Prompt Design**: Used distinct system and summary prompts to control persona and output format.
*   **Product Thinking**: Focused on a complete support lifecycle—from query to structured ticket.
*   **Practicality**: Prioritized local models for cost-effective, high-performance deployment.
