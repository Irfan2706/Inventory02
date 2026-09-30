from __future__ import annotations


SUMMARY_THRESHOLD = 2000


def load_summarize_chain():
    """Return an optional LangChain summarizer without requiring a new model locally."""
    return None


def _summarize_if_long(text: str) -> str:
    if len(text) <= SUMMARY_THRESHOLD:
        return text

    try:
        chain = load_summarize_chain()
        if chain is not None:
            summary = chain.run(text)
            if isinstance(summary, str) and summary.strip():
                return summary.strip()
    except Exception:
        pass

    # Keep the fallback deterministic and local when no summarization model is available.
    return text[:SUMMARY_THRESHOLD].rsplit(" ", 1)[0].rstrip() + "..."
