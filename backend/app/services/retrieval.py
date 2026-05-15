import ast
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from app.core.llm_setup import get_utility_llm

class GradeDocuments(BaseModel):
    binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")


def grade_relevance(question: str, documents: list[str]) -> tuple[list[str], bool]:
    """CRAG: Grade document relevance. Internal docs only."""

    valid_docs = []
    docs_to_grade = []

    # 1. Immediate Bypass for Structured Data & Metadata Match
    for doc in documents:
        doc_str = str(doc)

        # Pass SQL and Graph results immediately
        if (isinstance(doc, list) and len(doc) > 0) or \
                (doc_str.startswith("SQL Result:") and "[]" not in doc_str):
            valid_docs.append(doc_str)
            continue

        # Parse Vector DB documents to check metadata
        try:
            if " | METADATA: " in doc_str:
                # Neatly unpack the string we created in query_construction.py
                content_str, meta_str = doc_str.split(" | METADATA: ", 1)
                content_str = content_str.replace("CONTENT: ", "", 1).strip()
                metadata = ast.literal_eval(meta_str.strip())

                q_lower = question.lower()
                source = metadata.get("source", "").lower()

                # WIDENED RULE: If the user asks for policies, and the source is ANY policy, pass it!
                if "policy" in q_lower and "policy" in source:
                    valid_docs.append(content_str)
                    continue
        except Exception:
            pass  # If parsing fails, fall back to LLM grading

        # If it didn't pass the deterministic checks, queue it for the LLM
        docs_to_grade.append(doc_str)

    # 2. Only run the LLM Grader if we actually have fuzzy documents to grade
    if docs_to_grade:
        llm = get_utility_llm(temperature=0)
        structured_llm = llm.with_structured_output(GradeDocuments)

        prompt = PromptTemplate(
            template="""You are an expert evaluator assessing the relevance of a retrieved document to a user's question.
            Document: {document}
            Question: {question}

            GRADING INSTRUCTIONS:
            1. DIRECT MATCH: If the document contains the explicit answer to the question, score 'yes'.
            2. PARTIAL/LIST AGGREGATION: If the question asks for a list, summary, or aggregation (e.g., 'list all', 'what are the', 'total number'), score 'yes' if the document contains ANY single piece of information that contributes to the final assembled answer. Do not reject a document just because it cannot answer the entire question alone.
            3. CATEGORICAL LENIENCY: Evaluate relevance based on semantic utility, not strict corporate taxonomy. If a document logically serves the user's broader intent (e.g., treating an 'InfoSec' or 'Ethics' rule as a general 'Company Policy'), score 'yes'.
            4. DATABASE OUTPUTS: If the document contains raw database relationships or entity lists that match the subjects in the question, score 'yes'.

            Give a binary score 'yes' or 'no' indicating if the document is relevant to the question."""
            ,
            input_variables=["document", "question"],
        )
        chain = prompt | structured_llm

        for doc_str in docs_to_grade:
            # Don't bother grading empty database results
            if doc_str == "[]" or doc_str == "SQL Result: []":
                continue

            # Strip metadata before showing the LLM so it doesn't get confused
            clean_doc_str = doc_str.split(" | METADATA: ")[0].replace("CONTENT: ", "",
                                                                      1).strip() if " | METADATA: " in doc_str else doc_str

            score = chain.invoke({"question": question, "document": clean_doc_str})
            if score.binary_score == "yes":
                valid_docs.append(clean_doc_str)

    return valid_docs, False