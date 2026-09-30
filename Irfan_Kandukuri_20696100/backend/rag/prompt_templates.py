from __future__ import annotations

try:
    from langchain_core.prompts import PromptTemplate
except ImportError:  # pragma: no cover - dependency is optional at import time
    PromptTemplate = None


INVENTORY_RAG_PROMPT_TEXT = """You are an inventory management expert assistant for a retail operations system (POC-07).
Answer questions about inventory policies, procurement procedures, stock management, and supplier guidelines
using only the provided context.

Context:
{context}

Question: {question}

If the information is not available, say: "I don't have that information in the inventory manual."
Provide specific rules, formulas, and thresholds where available.

Answer:"""


def build_inventory_prompt() -> object:
    if PromptTemplate is None:
        raise RuntimeError("LangChain is required to build the inventory prompt template.")
    return PromptTemplate(input_variables=["context", "question"], template=INVENTORY_RAG_PROMPT_TEXT)


INVENTORY_RAG_PROMPT = build_inventory_prompt() if PromptTemplate is not None else None
