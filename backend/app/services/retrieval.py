from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from app.core.llm_setup import get_utility_llm

class GradeDocuments(BaseModel):
    binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")


def grade_relevance(question: str, documents: list[str]) -> tuple[list[str], bool]:
    """CRAG: Grade document relevance. Internal docs only."""

    valid_docs = []
    docs_to_grade = []

    # 1. Immediate Bypass for Structured Data
    for doc in documents:
        # If the document is an actual Python list (from Neo4j) and it's not empty
        if isinstance(doc, list) and len(doc) > 0:
            valid_docs.append(str(doc))
        # If the document is a string starting with SQL Result
        elif isinstance(doc, str) and doc.startswith("SQL Result:") and "[]" not in doc:
            valid_docs.append(doc)
        # Otherwise, it needs LLM grading (Vector DB chunks or empty lists)
        else:
            docs_to_grade.append(str(doc))

    # 2. Only run the LLM Grader if we actually have fuzzy documents to grade
    if docs_to_grade:
        llm = get_utility_llm(temperature=0)
        structured_llm = llm.with_structured_output(GradeDocuments)

        prompt = PromptTemplate(
            template="You are a grader assessing relevance of a retrieved document to a user question.\n"
                     "Document: {document}\nQuestion: {question}\n"
                     "Give a binary score 'yes' or 'no' indicating if the document is relevant.",
            input_variables=["document", "question"],
        )
        chain = prompt | structured_llm

        for doc_str in docs_to_grade:
            # Don't bother grading empty database results
            if doc_str == "[]" or doc_str == "SQL Result: []":
                continue

            score = chain.invoke({"question": question, "document": doc_str})
            if score.binary_score == "yes":
                valid_docs.append(doc_str)

    return valid_docs, False