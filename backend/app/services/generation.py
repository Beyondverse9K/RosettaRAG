from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from app.core.llm_setup import get_generator_llm, get_utility_llm

class GradeHallucinations(BaseModel):
    binary_score: str = Field(description="Answer is grounded in the facts, 'yes' or 'no'")

def generate_answer(question: str, documents: list[str], messages: list = None) -> str:
    """Standard RAG generation with INR currency formatting and Corporate Policy guardrails."""
    llm = get_generator_llm(temperature=0.3)
    docs_str = "\n\n".join(documents)

    # Format chat history
    history_str = ""
    if messages and len(messages) > 1:
        history_str = "--- CONVERSATION HISTORY ---\n"
        # We exclude the last message since it's the current question
        for msg in messages[:-1]:
            role = "User" if msg.type == "human" else "Assistant"
            history_str += f"{role}: {msg.content}\n"
        history_str += "----------------------------\n"

    prompt = (
        f"Answer the question based ONLY on the provided context.\n"
        f"MISSING DATA: If the context explicitly states that no relevant documents were found, reply exactly with: 'That Information is not present in my knowledge base'. Do NOT trigger the corporate guardrail.\n"
        f"CRITICAL INSTRUCTION: If the context contains raw database output, such as a SQL Result (e.g., `[('Name',)]`) or Neo4j JSON (e.g., `[{{'e.name': 'Name'}}]`), you MUST treat those raw values as the factual answer to the user's question and output them confidently in a natural sentence. Do NOT trigger the corporate guardrail if you see raw database results.\n"
        f"DEDUPLICATION & AGGREGATION OVERRIDE: If the context contains a raw list of entities or aggregated numbers (e.g., `[{{'Project': 'Name'}}]` or `[{{'SubordinateCount': 5}}]`), you MUST ASSUME the database correctly pre-filtered and calculated them based on the user's exact criteria. Output the information confidently as the answer, even if the filtering criteria (like department names) are not explicitly visible in the context.\n"
        f"IMPORTANT: All monetary values must be formatted as Indian Rupees (INR) using the ₹ symbol "
        f"and the Indian numbering system (e.g., ₹5,00,00,000).\n\n"
        f"{history_str}\n"
        f"Context: {docs_str}\n"
        f"Question: {question}\n"
        f"Answer:"
    )

    res = llm.invoke(prompt)
    return res.content

def check_hallucination(generation: str, documents: list[str]) -> bool:
    """Self-RAG: Ensure generation is grounded in retrieved documents."""

    # Bypass hallucination check for standard refusal message
    if "against our guidelines" in generation.lower() or "not present in my knowledge base" in generation.lower():
        return True

    llm = get_utility_llm(temperature=0)
    structured_llm = llm.with_structured_output(GradeHallucinations)

    prompt = PromptTemplate(
        template="You are a grader assessing whether an LLM generation is grounded in retrieved facts.\n"
                 "Facts: {documents}\nGeneration: {generation}\n"
                 "Give a binary score 'yes' or 'no'. 'yes' means it is grounded.",
        input_variables=["generation", "documents"],
    )
    chain = prompt | structured_llm
    docs_str = "\n\n".join(documents)
    score = chain.invoke({"documents": docs_str, "generation": generation})

    return score.binary_score == "yes"