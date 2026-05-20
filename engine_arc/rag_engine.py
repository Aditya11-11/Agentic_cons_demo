"""
This module gives our assistant 'knowledge'. 
It manages the vector database (ChromaDB) which lets us search through 
uploaded documents to find relevant answers to support questions.
"""
import chromadb
from chromadb.utils import embedding_functions
import pypdf
import os

class RAGEngine:
    """
    Handles document ingestion and information retrieval using 
    semantic search via ChromaDB.
    """
    def __init__(self, persist_directory="./chroma_db"):
        """
        Connects to the local database and sets up the embedding model 
        that converts text into searchable numbers.
        """
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self.collection = self.client.get_or_create_collection(
            name="support_docs", 
            embedding_function=self.emb_fn
        )

    def add_document(self, file_path):
        """
        Takes a PDF or Text file, reads the content, breaks it into smaller chunks, 
        and stores them in our memory for future searches.
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
        # Csplit by line
        chunks = [c for c in content.split("\n\n") if c.strip()]
        ids = [f"{filename}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": filename} for _ in chunks]
        
        self.collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas
        )

    def query(self, text, n_results=3):
        """
        Given a user's question, find the top 3 most relevant sections 
        from our stored documents to help the AI answer accurately.
        """
        results = self.collection.query(
            query_texts=[text],
            n_results=n_results
        )
        return "\n".join(results["documents"][0]) if results["documents"] else ""
