from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from agent.agent_service import answer_question


router = APIRouter()


class AgentQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class AgentQueryResponse(BaseModel):
    answer: str
    tools_used: list[str]
    reasoning: str


@router.post("/query", response_model=AgentQueryResponse)
def query_agent(
    payload: AgentQueryRequest,
    request: Request,
    _user=Depends(get_current_user),
):
    return answer_question(payload.question, request.headers.get("authorization"))
