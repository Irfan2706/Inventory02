def test_rag_query_endpoint(client, auth_headers, monkeypatch):
    from app.routers import rag as rag_router

    def fake_ask_question(question: str):
        assert question == "What is reorder point?"
        return {
            "answer": "The reorder point is the stock level at which replenishment begins.",
            "source_documents": [
                {
                    "source": "inventory_manual.md",
                    "chunk_index": 3,
                    "section": "Section 3: Stock Levels and Reorder Points",
                    "content": "The reorder_point is the stock level at which a replenishment order should be initiated.",
                }
            ],
        }

    monkeypatch.setattr(rag_router, "ask_question", fake_ask_question)

    response = client.post(
        "/api/v1/rag/query",
        json={"question": "What is reorder point?"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The reorder point is the stock level at which replenishment begins."
    assert data["sources"][0]["source"] == "inventory_manual.md"
    assert data["sources"][0]["chunk_index"] == 3
