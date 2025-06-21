Run the application from backend folder

uvicorn app.main:app --reload --reload-dir=app

To Retrain

1. Delete chroma_store folder
2. Add/Remove datasets from app/datasets folder
2. curl -X POST http://localhost:8000/initialize