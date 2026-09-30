from multi_agent import model_provider


def test_reset_llm_cache_clears_state():
    model_provider._cached_llm = object()
    model_provider._llm_checked = True
    model_provider.reset_llm_cache()
    assert model_provider._cached_llm is None
    assert model_provider._llm_checked is False


def test_get_local_llm_returns_none_when_chatollama_unavailable(monkeypatch):
    model_provider.reset_llm_cache()
    monkeypatch.setattr(model_provider, "ChatOllama", None)
    assert model_provider.get_local_llm() is None


def test_get_local_llm_returns_none_when_no_model_selected(monkeypatch):
    model_provider.reset_llm_cache()
    monkeypatch.setattr(model_provider, "ChatOllama", object)
    monkeypatch.setattr("rag.rag_chain._get_ollama_base_url", lambda: "http://localhost:11434")
    monkeypatch.setattr("rag.rag_chain._list_ollama_models", lambda base_url: [])
    monkeypatch.setattr("rag.rag_chain._select_chat_model", lambda models: None)
    assert model_provider.get_local_llm() is None


def test_get_local_llm_creates_chatollama_when_model_selected(monkeypatch):
    model_provider.reset_llm_cache()
    created = {}

    class FakeChatOllama:
        def __init__(self, model, base_url, temperature):
            created["model"] = model
            created["base_url"] = base_url
            created["temperature"] = temperature

    monkeypatch.setattr(model_provider, "ChatOllama", FakeChatOllama)
    monkeypatch.setattr("rag.rag_chain._get_ollama_base_url", lambda: "http://localhost:11434")
    monkeypatch.setattr("rag.rag_chain._list_ollama_models", lambda base_url: ["llama3"])
    monkeypatch.setattr("rag.rag_chain._select_chat_model", lambda models: "llama3")

    llm = model_provider.get_local_llm()
    assert isinstance(llm, FakeChatOllama)
    assert created["model"] == "llama3"

    # Second call should return the cached instance without re-selecting.
    assert model_provider.get_local_llm() is llm


def test_get_local_llm_returns_none_on_unexpected_exception(monkeypatch):
    model_provider.reset_llm_cache()
    monkeypatch.setattr(model_provider, "ChatOllama", object)
    monkeypatch.setattr(
        "rag.rag_chain._get_ollama_base_url",
        lambda: (_ for _ in ()).throw(RuntimeError("ollama unreachable")),
    )
    assert model_provider.get_local_llm() is None
