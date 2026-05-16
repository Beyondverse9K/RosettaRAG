import re
from langchain_community.utilities import SQLDatabase
from langchain_classic.chains import create_sql_query_chain
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from app.core.llm_setup import get_query_llm
from app.core.config import settings
from app.services.indexing import get_vectorstore
from app.services.query_translation import generate_hyde_document
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Keep-alive added to SQL to prevent timeouts
db = SQLDatabase.from_uri(
    settings.DATABASE_URL,
    engine_args={"pool_pre_ping": True, "pool_recycle": 300}
) if settings.DATABASE_URL else None

try:
    graph = Neo4jGraph(
        url=settings.NEO4J_URI,
        username=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD
    ) if settings.NEO4J_URI else None
    if graph:
        original_query = graph.query
        def read_only_query(query, params=None):
            params = params or {}
            # Regex to catch any mutating Cypher keywords (case-insensitive)
            forbidden_pattern = re.compile(r'\b(CREATE|MERGE|SET|DELETE|REMOVE|DROP|CALL)\b', re.IGNORECASE)
            if forbidden_pattern.search(query):
                print(f"\nBLOCKED MALICIOUS CYPHER ATTEMPT:\n{query}\n")
                # Return a harmless fake result to satisfy LangChain's parser
                return [{"error": "Write operations are strictly prohibited on this database."}]
            # If safe, execute normally
            return original_query(query, params)
        # Override LangChain's default graph.query method with our sandboxed version
        graph.query = read_only_query
except Exception as e:
    print(f"CRITICAL: Neo4j Connection Failed: {e}")
    graph = None

def retrieve_from_sql(question: str) -> str:
    """Text-to-SQL execution."""
    if not db: return "SQL DB not configured."
    llm = get_query_llm()
    chain = create_sql_query_chain(llm, db, k=151)
    try:
        query = chain.invoke({"question": question})
        clean_query = query.replace("```sql", "").replace("```", "").replace("SQLQuery:", "").strip()
        return f"SQL Result: {db.run(clean_query)}"
    except Exception as e:
        return f"SQL Error: {str(e)}"


def retrieve_from_graph(question: str) -> str:
    """Text-to-Cypher execution."""
    if not graph: return "Graph DB not configured."
    llm = get_query_llm()

    # Custom QA Prompt
    qa_template = """You are an assistant answering questions based on database results.
    The information below is the EXACT answer to the user's question, even if the context seems brief. 
    If the information contains a name or a value, formulate it confidently as the final answer. Do NOT apologize.
    Information: {context}
    Question: {question}
    Helpful Answer:"""
    qa_prompt = PromptTemplate(template=qa_template, input_variables=["context", "question"])

    # Custom Cypher Generation Prompt (Forces fuzzy matching)
    cypher_template = """Task:Generate Cypher statement to query a graph database.
            Instructions:
            Use only the provided relationship types and properties in the schema.
            IMPORTANT: When filtering by strings (like names or project titles), use the CONTAINS operator and toLower() to make the search case-insensitive and fuzzy (e.g., WHERE toLower(p.name) CONTAINS toLower('Zenith')).
            CRITICAL ID MATCHING: If the user query specifies an ID (e.g., "ID P3" or "employee 149"), you MUST filter against the `id` property (e.g., WHERE p.id = 'P3' OR e.id = 149). DO NOT use the `name` property for IDs.
            NLP CLEANUP: If a user asks a question with a possessive name (e.g., "Julie Stewart's" or "Julie Stewarts subordinates"), you MUST strip the trailing 's' or "'s" before putting the name in the CONTAINS clause (e.g., use 'Julie Stewart', NOT 'Julie Stewarts').
            CRITICAL: Always return the name of the searched entity alongside the results (e.g., RETURN e.name, p.name, p.status) so the final context clearly shows who the data belongs to.
            SHOW YOUR WORK: When possible, include the filtered properties in your RETURN statement (e.g., RETURN p.name AS Project, e.dept AS Dept) so the generator sees the context. CRITICAL EXCEPTIONS: Do NOT attempt to return variables that are scoped inside subqueries (like EXISTS) or variables that would break an aggregation grouping (like count()). For complex queries, it is perfectly acceptable to just RETURN DISTINCT the final target.
            DEDUPLICATION: Always use the DISTINCT keyword in your RETURN statements (e.g., RETURN DISTINCT p.name) to prevent duplicate rows from overwhelming the system, unless you are using an aggregation function like count().
            
            COMPLEX EXAMPLES:
            1. Manager to Subordinate's Projects: "What projects are Julie Stewart's subordinates contributing to?"
               MATCH (sub:Employee)-[:REPORTS_TO]->(mgr:Employee) WHERE toLower(mgr.name) CONTAINS toLower('Julie Stewart') MATCH (sub)-[:CONTRIBUTES_TO]->(p:Project) RETURN mgr.name AS Manager, sub.name AS Subordinate, p.name AS Project

            2. Leader to Project Contributors: "Who is working on the project led by Katrina Chen?"
               MATCH (leader:Employee)-[:LEADS]->(p:Project)<-[:CONTRIBUTES_TO]-(contributor:Employee) WHERE toLower(leader.name) CONTAINS toLower('Katrina Chen') RETURN leader.name AS Leader, p.name AS Project, contributor.name AS Contributor

            3. Project to Leader's Subordinates: "Who reports to the leader of Project Quantum Forge?"
               MATCH (sub:Employee)-[:REPORTS_TO]->(leader:Employee)-[:LEADS]->(p:Project) WHERE toLower(p.name) CONTAINS toLower('Quantum Forge') RETURN p.name AS Project, leader.name AS Leader, sub.name AS DirectReport

            4. Cross-Departmental Dependencies (WITH clause): "What distinct projects are being contributed to by both the Engineering department and the Finance department?"
               MATCH (e1:Employee)-[:CONTRIBUTES_TO]->(p:Project) WHERE toLower(e1.dept) CONTAINS toLower('engineering') WITH p MATCH (e2:Employee)-[:CONTRIBUTES_TO]->(p) WHERE toLower(e2.dept) CONTAINS toLower('finance') RETURN DISTINCT p.name AS Project, 'Engineering' AS Dept1, 'Finance' AS Dept2

            5. Aggregation and Sorting (COUNT): "Which manager has the most direct reports contributing to Project Vanguard?"
               MATCH (sub:Employee)-[:REPORTS_TO]->(mgr:Employee) MATCH (sub)-[:CONTRIBUTES_TO]->(p:Project) WHERE toLower(p.name) CONTAINS toLower('vanguard') RETURN mgr.name AS Manager, count(sub) AS SubordinateCount ORDER BY SubordinateCount DESC LIMIT 1

            6. Second-Degree Traversal: "Who reports to the direct reports of Jamie Brown?"
               MATCH (sub2:Employee)-[:REPORTS_TO]->(sub1:Employee)-[:REPORTS_TO]->(mgr:Employee) WHERE toLower(mgr.name) CONTAINS toLower('jamie brown') RETURN mgr.name AS Executive, sub1.name AS Director, sub2.name AS DirectReport

            7. Negation and Isolation (NOT EXISTS): "Which employees from the Engineering department are contributing to a project, but no one else from Engineering is contributing to that same project?"
               MATCH (e:Employee)-[:CONTRIBUTES_TO]->(p:Project) WHERE toLower(e.dept) CONTAINS toLower('engineering') AND NOT EXISTS {{ MATCH (other:Employee)-[:CONTRIBUTES_TO]->(p) WHERE toLower(other.dept) CONTAINS toLower('engineering') AND other <> e }} RETURN e.name AS IsolatedEmployee, p.name AS Project, e.dept AS Department

            Schema:
            {schema}

            The question is:
            {question}"""
    cypher_prompt = PromptTemplate(template=cypher_template, input_variables=["schema", "question"])

    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
        top_k=50,
        allow_dangerous_requests=True,
        return_direct=True,
        qa_prompt=qa_prompt,
        cypher_prompt=cypher_prompt
    )
    try:
        res = chain.invoke({"query": question})
        return res.get("result", "No graph results found.")
    except Exception as e:
        return f"Graph Error: {str(e)}"


def retrieve_from_vector(question: str) -> list[str]:
    """Self-query / HyDE Vector retrieval with Score Threshold."""
    try:
        vectorstore = get_vectorstore()
        hyde_doc = generate_hyde_document(question)

        # Ask Pinecone to return the similarity score alongside the documents
        results = vectorstore.similarity_search_with_score(hyde_doc, k=15)

        valid_docs = []
        for doc, score in results:
            # Only keep documents that are an actual strong semantic match
            if score >= 0.60:
                valid_docs.append(f"CONTENT: {doc.page_content} | METADATA: {doc.metadata}")

        return valid_docs
    except Exception as e:
        return [f"Vector Retrieval Error: {str(e)}"]

# Agentic Multi-Hop Retrieval
@tool
def search_sql_db(query: str) -> str:
    """Use this to find exact employee names, salaries, departments, or budgets.
    CRITICAL: The input MUST be a natural language question (e.g., 'What is the sum of salaries for John and Mary?'), NEVER a raw SQL query."""
    return retrieve_from_sql(query)

@tool
def search_graph_db(query: str) -> str:
    """Use this to find reporting lines, who reports to whom, or project leadership.
    CRITICAL: The input MUST be a natural language question (e.g., 'What projects does John lead?'), NEVER a raw Cypher query."""
    return retrieve_from_graph(query)

@tool
def search_vector_db(query: str) -> str:
    """Use this to find company policies, IT standards, or project wikis.
    CRITICAL: The input MUST be a complete natural language question (e.g., 'What is the technical scope of Project X?')."""
    docs = retrieve_from_vector(query)
    return "\n\n".join(docs) if docs else "No documents found."

def retrieve_multi_hop(question: str, messages: list = None) -> str:
    """Agentic loop that queries databases sequentially based on LLM reasoning and history."""
    llm = get_query_llm()
    tools = [search_sql_db, search_graph_db, search_vector_db]
    system_msg = (
        "You are a sequential data retrieval agent for Chromatic Prism Corp. "
        "Break the user's complex question down into steps and use your tools ONE AT A TIME to gather context across databases.\n\n"
        """Always verify the user's claims about an entity's role, department, relationship like leading, contributing or reporting, 
        and policy specific information before proceeding to the next hop. For example, if the user asks about 'the highest-paid employee
        in Operations', your first step should be to query the SQL database to confirm the employee's name and department. Only after 
        confirming that information should you proceed to query the graph database about that specific employee's projects, and then 
        the vector database for project details.\n\n"""
        "### MULTI-HOP REASONING STRATEGIES & EXAMPLES:\n"
        "1. Budget-to-Wiki Pipeline (SQL -> Graph -> Vector):\n"
        "   - User: 'Identify the highest-paid employee in Operations. What project do they lead, and what is the authorized budget?'\n"
        "   - Hop 1 (search_sql_db): Find the highest-paid employee in Operations to get the name.\n"
        "   - Hop 2 (search_graph_db): Find the projects led by that specific employee name.\n"
        "   - Hop 3 (search_vector_db): Extract the budget and phase for that specific project from the wiki.\n\n"

        "2. Cross-Departmental Intersection (Graph -> SQL):\n"
        "   - User: 'Identify all employees who directly report to the CEO. What is the combined operating budget of their departments?'\n"
        "   - Hop 1 (search_graph_db): Find direct reports to the CEO to get a list of names.\n"
        "   - Hop 2 (search_sql_db): Find the total operating budget for the distinct departments those specific individuals belong to.\n\n"

        "3. Tech Scope to Payroll Calculation (Vector -> Graph -> SQL):\n"
        "   - User: 'Which project involves a scalable social network, and what is the combined salary of its contributors?'\n"
        "   - Hop 1 (search_vector_db): Query the wiki for 'scalable social network' to get the Project Name.\n"
        "   - Hop 2 (search_graph_db): Find all employees contributing to that Project Name to get a list of names.\n"
        "   - Hop 3 (search_sql_db): Calculate the sum of salaries for those specific contributing employees.\n\n"

        "4. Deep Hierarchy & Policy Check (SQL -> Graph -> Vector):\n"
        "   - User: 'Find the department with the smallest operating budget. Who is the manager of its leader, and what are the CFO notification rules for their projects?'\n"
        "   - Hop 1 (search_sql_db): Find the leader of the department with the smallest budget.\n"
        "   - Hop 2 (search_graph_db): Find the manager of that leader AND the projects the leader leads.\n"
        "   - Hop 3 (search_vector_db): Extract the CFO oversight rules for those specific projects.\n\n"

        "5. Multi-Disciplinary Project Filter (SQL -> Graph):\n"
        "   - User: 'Are there any projects contributed to by both Marketing and Engineering? Who leads them?'\n"
        "   - Hop 1 (search_sql_db): Get lists of employee names/IDs for the Marketing and Engineering departments.\n"
        "   - Hop 2 (search_graph_db): Find Project nodes with incoming CONTRIBUTES_TO edges from BOTH lists, and identify the project manager.\n\n"

        "Once you have gathered all factual information required to answer the main question, output the combined facts clearly."
    )

    agent_executor = create_react_agent(llm, tools, prompt=system_msg)

    # Give the agent access to the full conversation memory
    agent_messages = []
    if messages:
        # KEEP ONLY THE LAST 6 MESSAGES (3 Question/Answer pairs)
        recent_messages = messages[-6:] if len(messages) > 6 else messages
        agent_messages.extend(recent_messages)
    else:
        agent_messages.append(("human", question))

    response = agent_executor.invoke({"messages": agent_messages})
    return response["messages"][-1].content