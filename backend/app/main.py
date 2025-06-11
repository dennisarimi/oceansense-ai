# File: app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from .rag_pipeline import RAGPipeline

app = FastAPI()
pipeline = RAGPipeline(dataset_dir="datasets")

class Question(BaseModel):
    query: str

@app.post("/ask")
def ask_question(q: Question):
    answer = pipeline.ask(q.query)
    return {"answer": answer}

@app.post("/initialize")
def initialize_dataset():
    success = pipeline.initialize_dataset()
    return {"initialized": success}
