"""
This module gives our assistant 'knowledge'.
It manages the vector database (ChromaDB) which lets us search through
uploaded documents to find relevant answers to support questions.

Improvements:
- Semantic chunking with sliding window + overlap
- Metadata-enriched chunks for better filtering
- Query expansion via LLM for improved recall
- Deduplicated multi-query retrieval
"""
import json
import chromadb
from chromadb.utils import embedding_functions
import pypdf
import os
from config import Config


# ─── Chunking Utilities ─────────────────────────────────────────────

def chunk_document(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    """
    Sliding window chunks with overlap to preserve context across boundaries.
    Target: ~400 words per chunk, 80-word overlap.
    """
    chunk_size = chunk_size or Config.RAG_CHUNK_SIZE
    overlap = overlap or Config.RAG_CHUNK_OVERLAP
    words = text.split()
    chunks = []
    step = max(chunk_size - overlap, 1)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def build_metadata(source_file: str, chunk_index: int, chunk_text: str) -> dict:
    """Attach metadata to every chunk for better retrieval filtering."""
    return {
        "source": source_file,
        "chunk_index": chunk_index,
        "char_count": len(chunk_text),
        "preview": chunk_text[:80],
    }


# ─── Query Expansion ────────────────────────────────────────────────

def expand_query(query: str, llm_engine) -> list[str]:
    """
    Generate 2 alternative phrasings of the user's query to improve RAG recall.
    """
    prompt = (
        f"Rephrase this support query in 2 different ways to maximize search coverage:\n"
        f"Query: {query}\n"
        f"Return as a JSON list of 2 strings. Example: [\"alt1\", \"alt2\"]"
    )
    raw = llm_engine.generate(prompt, max_new_tokens=80)
    try:
        alternatives = json.loads(raw)
        return [query] + alternatives[:2]
    except Exception:
        return [query]


def retrieve_with_expansion(query: str, collection, llm_engine, top_k: int = None) -> str:
    """
    Retrieve using original + expanded queries, deduplicate, return as context string.
    """
    top_k = top_k or Config.RAG_TOP_K
    queries = expand_query(query, llm_engine)
    seen_ids = set()
    results = []
    for q in queries:
        try:
            res = collection.query(query_texts=[q], n_results=top_k)
            for doc, meta, dist in zip(
                res["documents"][0], res["metadatas"][0], res["distances"][0]
            ):
                uid = meta.get("source", "") + str(meta.get("chunk_index", ""))
                if uid not in seen_ids:
                    seen_ids.add(uid)
                    results.append({"text": doc, "distance": dist, "meta": meta})
        except Exception:
            continue

    # Sort by relevance (lower distance = better)
    results.sort(key=lambda x: x["distance"])
    top = results[:top_k]
    return "\n\n---\n\n".join(
        f"[Source: {r['meta'].get('source', '?')}]\n{r['text']}" for r in top
    )


# ─── RAG Engine ──────────────────────────────────────────────────────

class RAGEngine:
    """
    Handles document ingestion and information retrieval using
    semantic search via ChromaDB.
    """
    def __init__(self, persist_directory=None):
        """
        Connects to the local database and sets up the embedding model
        that converts text into searchable vectors.
        """
        persist_directory = persist_directory or Config.CHROMA_PERSIST_DIR
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=Config.EMBEDDING_MODEL
        )
        self.collection = self.client.get_or_create_collection(
            name="support_docs",
            embedding_function=self.emb_fn
        )

    def add_document(self, file_path: str):
        """
        Takes a PDF or Text file, reads the content, breaks it into
        overlapping semantic chunks, and stores them with metadata.
        """
        filename = os.path.basename(file_path)
        content = ""
        if file_path.endswith(".pdf"):
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    content += page.extract_text() + "\n"
        elif file_path.endswith(".txt"):
            with open(file_path, "r") as f:
                content = f.read()

        # Semantic chunking with overlap
        chunks = chunk_document(content)
        ids = [f"{filename}_{i}" for i in range(len(chunks))]
        metadatas = [build_metadata(filename, i, c) for i, c in enumerate(chunks)]

        if chunks:
            self.collection.add(
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )

    def query(self, text: str, n_results: int = None) -> str:
        """
        Given a user's question, find the most relevant sections
        from our stored documents to help the AI answer accurately.
        """
        n_results = n_results or Config.RAG_TOP_K
        results = self.collection.query(
            query_texts=[text],
            n_results=n_results
        )
        return "\n".join(results["documents"][0]) if results["documents"] else ""

