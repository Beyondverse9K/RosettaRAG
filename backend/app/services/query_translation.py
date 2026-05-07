from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.llm_setup import get_query_llm

def generate_hyde_document(query: str) -> str:
    """HyDE: Generate hypothetical document to improve vector retrieval."""
    llm = get_query_llm(temperature=0.2)
    prompt = PromptTemplate.from_template(
        "You are writing a snippet for the Chromatic Prism Corp internal company wiki.\n"
        "Please write a brief, 2-3 sentence hypothetical passage that perfectly answers the following employee question.\n"
        "Write in a dry, corporate tone as if you are quoting an HR policy, IT standard, or Project Wiki document.\n"
        "Question: {question}\nPassage:"
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"question": query})

def decompose_query(query: str) -> list[str]:
    """Multi-query: Decompose input question into sub-questions."""
    llm = get_query_llm(temperature=0.2)
    prompt = PromptTemplate.from_template(
        "Generate 4 distinct sub-questions that help answer this main question: {question}"
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"question": query})
    return [q.strip() for q in response.split("\n") if q.strip()]