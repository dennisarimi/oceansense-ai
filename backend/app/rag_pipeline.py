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
    You are a marine data analyst summarizing time-series oceanographic sensor data. Provide summarized answers that describe patterns or trends.
    <</SYS>>

    Context:
    {context}

    Question: {query}
    Summarize if multiple values are given. Provide trends, not just isolated numbers.
    [/INST]"""
        return self.llm.generate_answer(prompt)
