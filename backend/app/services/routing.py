from pydantic import BaseModel, Field
from app.core.llm_setup import get_utility_llm

class RouteQuery(BaseModel):
    datasource: str = Field(...,description="Choose 'vector_db', 'graph_db', 'relational_db', 'multi_hop' or 'reject' if about another company or unrelated general knowledge.",)

def route_question(question: str, messages: list = None) -> str:
    llm = get_utility_llm(temperature=0)
    structured_llm = llm.with_structured_output(RouteQuery)

    system_msg = """You are an expert router for the Chromatic Prism Corp internal AI assistant. 
    Route the user question to the strictly correct datasource.

    IMPORTANT CORPORATE POLICY & DOMAIN RESTRICTIONS: 
    1. If the question does NOT mention a company name, ASSUME it is about 'Chromatic Prism Corp' ONLY IF the topic is relevant to an internal corporate context (e.g., HR, IT, projects, employees, budgets).
    2. If the question explicitly mentions 'Chromatic Prism Corp', route to the correct internal DB.
    3. If the question explicitly asks about a DIFFERENT company (e.g., Apple, Google, Microsoft), you MUST route it to 'reject'.
    4. DOMAIN REJECTION: If the question is general knowledge, coding, math, or COMPLETELY UNRELATED to internal data (e.g., "explain greedy algorithms", "stock prices"), you MUST route it to 'reject'.

    Datasource Rules:
    1. relational_db: ONLY for questions about exact employee names, salaries, departments, IDs, budgets, or roles. 
    2. graph_db: For questions about reporting lines, 'who reports to whom', or 'who leads which projects' or 'who contributes to which projects'.
    3. vector_db: For all questions about company policies, benefits, hardware, IT standards, or project wikis which includes phase and budget, team composition and technical scope.
    4. reject: Use when a foreign company name is mentioned, or the question is completely out-of-domain.
    5. multi_hop: Use ONLY when a single question requires combining data across multiple databases (SQL, Graph, Vector).
       EXAMPLES of multi_hop:
       - "Identify the highest-paid employee (SQL) and list the projects they lead (Graph)."
       - "What is the budget (Vector) of the project led by the CEO's direct reports (Graph)?"
       - "Which project's technical scope is 'social network' (Vector), and what is the total salary of its contributors (SQL + Graph)?"
       - "Find the department with the lowest budget (SQL). Who is the manager of its leader (Graph)?"
       - "Are there projects contributed to by both Marketing and Engineering (SQL + Graph)?"
    """

    # Format chat history for context
    formatted_messages = [{"role": "system", "content": system_msg}]
    if messages:
        # KEEP ONLY THE LAST 6 MESSAGES (3 Question/Answer pairs)
        recent_messages = messages[-6:] if len(messages) > 6 else messages

        # Exclude the very last message since it's the current question
        for msg in recent_messages[:-1]:
            role = "user" if msg.type == "human" else "assistant"
            formatted_messages.append({"role": role, "content": msg.content})

    formatted_messages.append({"role": "user", "content": question})

    route = structured_llm.invoke(formatted_messages)
    return route.datasource