from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.core.config import settings
from app.services.routing import route_question
from app.services.query_construction import retrieve_from_sql, retrieve_from_graph, retrieve_from_vector
from app.services.retrieval import grade_relevance
from app.services.generation import generate_answer, check_hallucination

class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[str]
    datasource: str
    retries: int  # Prevents infinite self-RAG loops


# --- 1. Node Functions ---

def reject_node(state):
    """Short-circuit node for out-of-domain questions. Costs 0 API calls."""
    return {
        "generation": "It is against our guidelines to answer questions not related to Chromatic Prism Corp."
    }

def route_node(state: GraphState):
    """Routes the question and initializes the retry counter."""
    ds = route_question(state["question"])
    return {"datasource": ds, "retries": 0}

def retrieve_node(state: GraphState):
    """Retrieves from the routed database."""
    ds = state["datasource"]
    question = state["question"]
    docs = []

    if ds == "relational_db":
        docs.append(retrieve_from_sql(question))
    elif ds == "graph_db":
        docs.append(retrieve_from_graph(question))
    else:
        docs.extend(retrieve_from_vector(question))

    return {"documents": docs}

def grade_node(state: GraphState):
    """Grades relevance."""
    valid_docs, _ = grade_relevance(state["question"], state["documents"])

    if not valid_docs:
        valid_docs = ["No highly relevant internal documents were found to answer this question."]

    return {"documents": valid_docs}

def generate_node(state: GraphState):
    """Generates the final answer and increments the retry counter."""
    answer = generate_answer(state["question"], state["documents"])
    return {"generation": answer, "retries": state.get("retries", 0) + 1}


# --- 2. Conditional Edge Logic ---

def route_condition(state: GraphState):
    """Routes the question based on the router's output."""
    if state.get("datasource") == "reject":
        return "reject_node"
    return "retrieve"

def grade_generation_v_documents(state: GraphState):
    """Self-RAG: Checks for hallucinations with a retry limit."""
    if state["retries"] >= 3:
        return "useful"
    is_grounded = check_hallucination(state["generation"], state["documents"])
    return "useful" if is_grounded else "not useful"


# --- 3. Build the Graph ---

workflow = StateGraph(GraphState)

workflow.add_node("route", route_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade", grade_node)
workflow.add_node("generate", generate_node)
workflow.add_node("reject_node", reject_node)

workflow.set_entry_point("route")

workflow.add_conditional_edges(
    "route",
    route_condition,
    {
        "retrieve": "retrieve",
        "reject_node": "reject_node"
    }
)

workflow.add_edge("retrieve", "grade")
workflow.add_edge("grade", "generate")

workflow.add_conditional_edges(
    "generate",
    grade_generation_v_documents,
    {"not useful": "generate", "useful": END}
)

workflow.add_edge("reject_node", END)


# --- 4. Configure PostgreSQL Memory Checkpointer ---

connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

# Create a connection pool using your Neon DATABASE_URL
pool = ConnectionPool(
    conninfo=settings.DATABASE_URL,
    max_size=20,
    kwargs=connection_kwargs,
)

# Configure the serializer to suppress the LangChain deprecation warning
custom_serializer = JsonPlusSerializer()

# Initialize the Postgres checkpointer
memory = PostgresSaver(pool, serde=custom_serializer)

# Automatically create the required tables in Neon if they don't exist
memory.setup()

# Compile the graph with persistent memory
app_graph = workflow.compile(checkpointer=memory)