from rag.ingest import build_chunk_documents, chunk_markdown_document, load_inventory_manual


def test_inventory_manual_chunks_to_at_least_twenty_documents():
    manual = load_inventory_manual()
    chunks = chunk_markdown_document(manual)

    assert len(chunks) >= 20
    assert any("Section 2: Product Catalog and SKU System" in chunk for chunk in chunks)
    assert any("Section 5: Purchase Order (PO) Process" in chunk for chunk in chunks)


def test_chunk_documents_add_metadata():
    documents = build_chunk_documents("# Heading\n\nFirst paragraph.\n\nSecond paragraph.")

    assert documents[0]["metadata"]["source"] == "inventory_manual.md"
    assert documents[0]["metadata"]["chunk_index"] == 1
    assert documents[0]["page_content"]
