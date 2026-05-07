from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.globals import set_llm_cache
from langchain_core.caches import InMemoryCache
from app.core.config import settings

# Save results locally
set_llm_cache(InMemoryCache())

# Uses flash-lite for routing, grading, and hallucination checks.
def get_utility_llm(temperature=0.0):
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        max_retries=10,
        timeout=120
    )

# Uses flash to write complex SQL, Cypher, and HyDE passages.
def get_query_llm(temperature=0.0):
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        max_retries=10,
        timeout=120
    )

# Uses flash to formulate the final answer and survive retry loops.
def get_generator_llm(temperature=0.3):
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        max_retries=10,
        timeout=120
    )
# Uses embeddings for chunk optimization
def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2-preview",
        task_type="retrieval_document",
        output_dimensionality=3072,
        google_api_key=settings.GEMINI_API_KEY
    )