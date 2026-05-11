from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as chat_router
from app.core.config import settings
from langchain_core.globals import set_debug
set_debug(True)
app = FastAPI(
    title="RosettaRAG Enterprise API",
    description="Multi-modal routing RAG system combining SQL, Graph, and Vector databases.",
    version="1.0.0"
)

# CORS configuration for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(chat_router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "RosettaRAG Backend is running securely."}
