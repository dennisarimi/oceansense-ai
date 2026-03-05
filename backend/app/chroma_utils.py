import uuid
import chromadb
from sentence_transformers import SentenceTransformer


class ChromaRetriever:
    def __init__(self, collection_name="onc_docs"):
        self.client = chromadb.PersistentClient(path="./chroma_store")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.collection = self.client.get_or_create_collection(
            name=collection_name)

    def add_documents(self, docs):
        embeddings = self.model.encode(docs, show_progress_bar=True)
        self.collection.add(
            documents=docs,
            embeddings=[e.tolist() for e in embeddings],
            ids=[f"{i}_{uuid.uuid4()}" for i in range(len(docs))]

        )

    def query(self, question, k=5):
        q_emb = self.model.encode([question])
        result = self.collection.query(
            query_embeddings=q_emb.tolist(), n_results=k)
        return result["documents"][0]

    def has_docs(self):
        return len(self.collection.get()["ids"]) > 0
