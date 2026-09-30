from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from rag.rag_chain import ask_question


router = APIRouter()


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class RagSource(BaseModel):
    source: str
    chunk_index: int | None = None
    section: str | None = None
    content: str


class RagQueryResponse(BaseModel):
    answer: str
    source_documents: list[RagSource]
    sources: list[RagSource]


@router.post("/query", response_model=RagQueryResponse)
def query_rag(
    payload: RagQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del db
    del current_user
    try:
        result = ask_question(payload.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard for external services
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to answer question") from exc

    sources = [RagSource(**source) for source in result.get("source_documents", [])]
    return RagQueryResponse(answer=result.get("answer", ""), source_documents=sources, sources=sources)
