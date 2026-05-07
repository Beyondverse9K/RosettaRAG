from pydantic import BaseModel, Field
from app.core.llm_setup import get_utility_llm

class RouteQuery(BaseModel):
    datasource: str = Field(...,description="Choose 'vector_db', 'graph_db', 'relational_db', or 'reject' if about another company or unrelated general knowledge.",)

def route_question(question: str) -> str:
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
    """

    route = structured_llm.invoke([
        {"role": "system", "content": system_msg},
        {"role": "user", "content": question}
    ])
    return route.datasource