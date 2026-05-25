# Voice Support Copilot: Technical Architecture & Flow

This document details the internal workings of the Voice Support Copilot, including how tickets are managed, how the conversational session is tracked, and the internal methods powering the LLM and RAG engines.

## 1. Orchestration (How It All Comes Together)
The core orchestration happens in `app.py` (and the CLI equivalent `main.py`). The `respond()` function acts as the central brain:
1. **Routing**: When a user speaks or types, the system first checks if a support ticket is actively being created (`ticket_flow.active`). If yes, it delegates the response to the `TicketFlowManager`.
2. **Intent Detection**: If no ticket is active, the system checks for conversational triggers (like the user responding "yes" after the assistant offered to create a ticket).
3. **Retrieval-Augmented Generation (RAG)**: For general questions, the user's input is passed to `retrieve_with_expansion()` (in the RAG Engine) to fetch relevant knowledge base constraints.
4. **LLM Generation**: The system dynamically combines the `SYSTEM_PROMPT`, the fetched RAG context, and the sliding window history (from `ContextWindowManager`) to generate Neha's response.
5. **TTS Output**: The raw LLM response is stripped of markdown/think tags using `clean_for_tts()` before being converted to audio.

---

## 2. Ticket Engine (`ticket_engine.py`)
The Ticket Engine is responsible for the foundational data structures of a support ticket. 
- **`SupportTicket` (Dataclass)**: This defines every field a ticket can hold. Fields include user basics (Name, Email), ticket metadata (ID, Status, Priority), and detailed technical inputs (Subject, Category, Steps to Reproduce, Expected/Actual Behavior, Conversation Summary, Tags).
- **`to_json()` / `to_markdown()`**: Export methods that serialize the ticket data into a machine-readable format or a nicely formatted markdown view for the UI.

---

## 3. Ticket Flow (`ticket_flow.py`)
This module handles the conversational intake of a ticket using the `TicketFlowManager`. It condenses standard intake forms into a natural back-and-forth dialogue consisting of 4 questions.

### Key Methods:
- **`start()`**: Initializes the ticket, generates a unique timestamp-based `TKT` ID, and outputs the first question (asking for the user's name).
- **`next(user_input)`**: The core state machine method advancing through the questions.
    - **Smart Corrections**: Checks if the user's current input is actually a correction of a *previous* field (e.g., "Actually, my name is Aditya" when asked for an email). If so, it repairs the past state.
    - **Filler Handling**: If the user just says "Sure" or "Go ahead", it smoothly says "No problem, just let me know your [field] when you're ready" instead of mistakenly recording "Sure" as their name.
- **`_extract_field(field, raw)`**: Uses the LLM to cleanly parse the user's natural language response. For example, extracting "aditya@example.com" from "yeah my email is aditya@example.com thanks". It strictly adheres to rules distinguishing between valid data, missing data, and affirmative fillers.
- **`_normalize_priority(raw)`**: Maps conversational urgency phrases into a strictly typed enum (LOW, MEDIUM, HIGH, CRITICAL).

**Post-Processing Enrichment**: Once `ticket_flow` finishes asking the 4 questions, `app.py` kicks in. It takes the full conversation history and uses **`LLMEngine.generate_support_summary()`** to automatically write the `Subject`, `Category`, `Steps to Reproduce`, and `Conversation Summary`, effortlessly completing the ticket.

---

## 4. Session & Context Window Management (`ContextWindowManager` in `llm_engine.py`)
LLMs have token limits, and sending the entire chat history repeatedly is expensive and slow. The `ContextWindowManager` dynamically handles this:
- **`add(role, content)`**: Adds a new message to a `deque`. It roughly limits tracking to `_estimate_tokens()`.
- **`_compress()`**: When the conversation crosses a defined token limit (`summarize_threshold`), the manager strips the *oldest half* of the conversation messages. It then queries the LLM to generate a concise "Earlier summary" of those lost messages. This summary is injected at the top of the history list.
- **`get_history_string()`**: Serializes the memory. It prepends the running summary (if it exists) followed by the recent uncompressed alternating interactions (`User`, `Alex`/`Neha`).

---

## 5. LLM Engine (`llm_engine.py`)
A wrapper around Hugging Face's serverless Inference API.
### Key Methods:
- **`generate_response(messages)`**: Takes a structured list of roles and contents and communicates with the Qwen3 model.
- **`generate(prompt)`**: A simple single-prompt wrapper used for quick background tasks like logic classification or extraction.
- **`generate_support_summary(conversation_history)`**: Evaluates the whole chat. Uses the `TICKET_SUMMARY_PROMPT` to ask the LLM to dump a beautifully formatted JSON string describing the technical nature of the incident.

---

## 6. RAG Engine (`rag_engine.py`)
Handles knowledge persistence and intelligent search via ChromaDB and sentence-transformers.
### Key Methods:
- **`add_document(file_path)`**: Reads documents and breaks them down using a `RecursiveCharacterTextSplitter`. This breaks the KB into chunks with a sliding overlap to make sure context isn't lost between boundaries.
- **`retrieve(query)`**: Standard vector similarity search against the DB.
- **`retrieve_with_expansion(query, collection, llm)`**: Pure user queries (e.g., "how to fix timeout") are sometimes too vague for good vector matching. This method first calls the LLM to generate a list of likely keywords and synonyms, appending them to the query to ensure deep document retrieval.

---

## 7. Prompts (`prompt.py`)
Centralized instructional prompts instructing the LLM on behavior.
- **`SYSTEM_PROMPT`**: The massive core persona prompt. Defines the identity (Neha), behavior (warm, empathetic, concise), and strictly integrates **Negative Constraints** (e.g., "Never invent refund status", "Never guess internal names") so the assistant remains hallucination-free and safe for production.
- **`TICKET_SUMMARY_PROMPT`**: The JSON-schema blueprint guiding the LLM how to parse a conversation into `category`, `subject`, `steps_to_reproduce`, `expected_behavior`, and `actual_behavior`.
- **`INTENT_CLASSIFIER_PROMPT`**: Used to quietly categorize user actions behind the scenes (e.g., identifying whether they are asking a `how_to_question` vs a `ticket_request`).
