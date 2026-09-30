from rag.prompt_templates import INVENTORY_RAG_PROMPT_TEXT
from rag.rag_chain import ask_question, serialize_source_documents


class DummyDocument:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


class FakeChain:
    def invoke(self, payload):
        assert payload["query"] == "What is reorder point?"
        return {
            "result": "The reorder point is the trigger level for replenishment.",
            "source_documents": [
                DummyDocument(
                    "The reorder point is the stock level at which a replenishment order should be initiated.",
                    {"source": "inventory_manual.md", "chunk_index": 3, "section": "Section 3"},
                )
            ],
        }


def test_prompt_enforces_inventory_manual_only_answers():
    assert "I don't have that information in the inventory manual." in INVENTORY_RAG_PROMPT_TEXT


def test_serialize_source_documents_keeps_metadata():
    sources = serialize_source_documents(
        [DummyDocument("Example content", {"source": "inventory_manual.md", "chunk_index": 1, "section": "Section 1"})]
    )

    assert sources == [
        {
            "source": "inventory_manual.md",
            "chunk_index": 1,
            "section": "Section 1",
            "content": "Example content",
        }
    ]


def test_ask_question_uses_supplied_chain():
    result = ask_question("What is reorder point?", chain=FakeChain())

    assert result["answer"] == "The reorder point is the trigger level for replenishment."
    assert result["source_documents"][0]["chunk_index"] == 3
    assert result["source_documents"][0]["section"] == "Section 3"
