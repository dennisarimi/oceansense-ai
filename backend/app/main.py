# File: app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .rag_pipeline import RAGPipeline

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
