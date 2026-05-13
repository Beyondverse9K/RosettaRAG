from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as chat_router
from app.core.config import settings
from app.graph.workflow import pool

from langchain_core.globals import set_debug
# Turned off for production to prevent log spam
set_debug(True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: pool is already initialized in workflow.py
    yield
    # Shutdown: Close the Neon connection pool gracefully
    if pool:
        pool.close()

app = FastAPI(
    title="RosettaRAG Enterprise API",
    description="Multi-modal routing RAG system combining SQL, Graph, and Vector databases.",
    version="1.0.0",
    lifespan=lifespan
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

@app.head("/")
@app.get("/")
def health_check():
    return {"status": "RosettaRAG Backend is running securely with Persistent Memory."}
