import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.graph.workflow import app_graph

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    datasource: str

def sanitize_input(text: str) -> str:
    """Removes special characters but keeps alphanumeric, spaces, and question marks."""
    # Keeps letters, numbers, spaces, hyphens, and question marks
    clean_text = re.sub(r'[^\w\s\?-]', '', text)
    return clean_text.strip()


@router.post("/chat", response_model=QueryResponse)
async def chat_endpoint(request: QueryRequest):
    try:
        clean_query = sanitize_input(request.query)
        inputs = {"question": clean_query}
        final_state = app_graph.invoke(inputs)
        return QueryResponse(
            answer=final_state.get("generation", "No answer generated."),
            datasource=final_state.get("datasource", "unknown")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))