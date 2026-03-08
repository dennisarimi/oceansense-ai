# File: app/rag_pipeline.py
from .chroma_utils import ChromaRetriever
from .mistral_utils import MistralLLM
from .data_utils import load_all_csvs, extract_metadata_from_file
import os

class RAGPipeline:
    def __init__(self, dataset_dir: str):
        self.retriever = ChromaRetriever()
        self.llm = MistralLLM()
        self.dataset_dir = dataset_dir

    def initialize_dataset(self):
        # 🔄 Reinitialize retriever
        self.retriever = ChromaRetriever()

        all_docs = []
        for fname in os.listdir(self.dataset_dir):
            if fname.endswith(".csv"):
                fpath = os.path.join(self.dataset_dir, fname)
                print(f"📥 Loading dataset: {fname}")
                metadata = extract_metadata_from_file(fpath)
                docs = load_all_csvs(dataset_dir=fpath, metadata=metadata)
                print(f"📄 Extracted {len(docs)} docs from {fname}")
                all_docs.extend(docs)

        print(f"📊 Total documents: {len(all_docs)}")

        BATCH_SIZE = 5000
        for i in range(0, len(all_docs), BATCH_SIZE):
            self.retriever.add_documents(all_docs[i:i + BATCH_SIZE])
            print(f"✅ Indexed batch {i // BATCH_SIZE + 1}")

        return True

    def ask(self, query: str):
        docs = self.retriever.query(query)
        context = "\n".join(docs)
        prompt = f"""[INST] <<SYS>>
    You are a helpful assistant with expertise in marine and oceanographic data analysis.
    First, determine whether the user's question is related to marine science, oceanography, or sensor data.
    - If it IS marine-related: use the provided context to summarize time-series oceanographic sensor data, describe patterns or trends, and use domain-appropriate language. Summarize if multiple values are given. Provide trends, not just isolated numbers.
    - If it is NOT marine-related: answer the question directly and concisely like a normal assistant. Do NOT reference the context below or use marine-specific language. Just give a straightforward answer.
    <</SYS>>

    Context:
    {context}

    Question: {query}
    [/INST]"""
        return self.llm.generate_answer(prompt)
