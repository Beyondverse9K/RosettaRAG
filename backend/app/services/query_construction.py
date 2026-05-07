from langchain_community.utilities import SQLDatabase
from langchain_classic.chains import create_sql_query_chain
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from app.core.llm_setup import get_query_llm
from app.core.config import settings
from app.services.indexing import get_vectorstore
from app.services.query_translation import generate_hyde_document
from langchain_core.prompts import PromptTemplate

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
except Exception as e:
    print(f"CRITICAL: Neo4j Connection Failed: {e}")
    graph = None

def retrieve_from_sql(question: str) -> str:
    """Text-to-SQL execution."""
    if not db: return "SQL DB not configured."
    llm = get_query_llm()
    chain = create_sql_query_chain(llm, db, k=50)
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
            NLP CLEANUP: If a user asks a question with a possessive name (e.g., "Julie Stewart's" or "Julie Stewarts subordinates"), you MUST strip the trailing 's' or "'s" before putting the name in the CONTAINS clause (e.g., use 'Julie Stewart', NOT 'Julie Stewarts').
            CRITICAL: Always return the name of the searched entity alongside the results (e.g., RETURN e.name, p.name, p.status) so the final context clearly shows who the data belongs to.
            SHOW YOUR WORK: When possible, include the filtered properties in your RETURN statement (e.g., RETURN p.name AS Project, e.dept AS Dept) so the generator sees the context. CRITICAL EXCEPTIONS: Do NOT attempt to return variables that are scoped inside subqueries (like EXISTS) or variables that would break an aggregation grouping (like count()). For complex queries, it is perfectly acceptable to just RETURN DISTINCT the final target.
            DEDUPLICATION: Always use the DISTINCT keyword in your RETURN statements (e.g., RETURN DISTINCT p.name) to prevent duplicate rows from overwhelming the system, unless you are using an aggregation function like count().
            
            MULTI-HOP & COMPLEX EXAMPLES:
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
        results = vectorstore.similarity_search_with_score(hyde_doc, k=6)

        valid_docs = []
        for doc, score in results:
            # Only keep documents that are an actual strong semantic match
            if score >= 0.70:
                valid_docs.append(doc.page_content)

        return valid_docs
    except Exception as e:
        return [f"Vector Retrieval Error: {str(e)}"]