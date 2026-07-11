from fastapi import FastAPI

app = FastAPI(
    title="Smart Document RAG API",
    description="Backend API for document-based question answering system.",
    version="0.1.0",
)


@app.get("/")
def read_root():
    return {
        "message": "Smart Document RAG API is running."
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }
