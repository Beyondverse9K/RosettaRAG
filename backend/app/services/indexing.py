from langchain_pinecone import PineconeVectorStore
from langchain_experimental.text_splitter import SemanticChunker
from app.core.llm_setup import get_embeddings
from app.core.config import settings

def get_vectorstore():
    """Returns the Pinecone vector store connection."""
    embeddings = get_embeddings()
    return PineconeVectorStore(
        index_name=settings.PINECONE_INDEX_NAME,
        embedding=embeddings,
        pinecone_api_key=settings.PINECONE_API_KEY
    )

def semantic_split_documents(docs):
    """Chunk Optimization: Semantic Splitter."""
    embeddings = get_embeddings()
    text_splitter = SemanticChunker(embeddings)
    return text_splitter.split_documents(docs)