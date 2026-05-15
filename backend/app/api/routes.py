import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.graph.workflow import app_graph
from langchain_core.messages import HumanMessage

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    thread_id: str = "default_session"  # Frontend should pass a unique ID per user

class QueryResponse(BaseModel):
    answer: str
    datasource: str

def sanitize_input(text: str) -> str:
    """Removes special characters but keeps alphanumeric, spaces, and question marks."""
    clean_text = re.sub(r'[^\w\s\?-]', '', text)
    return clean_text.strip()


@router.post("/chat", response_model=QueryResponse)
async def chat_endpoint(request: QueryRequest):
    try:
        clean_query = sanitize_input(request.query)
        # Pass the query natively as a HumanMessage to initialize memory tracking
        inputs = {
            "question": clean_query,
            "messages": [HumanMessage(content=clean_query)]
        }
        config = {"configurable": {"thread_id": request.thread_id}}
        final_state = app_graph.invoke(inputs, config=config)
        # Extract the final AIMessage from the conversation memory
        final_generation = final_state.get("generation", "No answer generated.")
        return QueryResponse(
            answer=final_generation,
            datasource=final_state.get("datasource", "unknown")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))