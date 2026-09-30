from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from mcp_server.chat_interface import process_message, sessions


router = APIRouter()


class MCPChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default", min_length=1, max_length=100)


class MCPChatResponse(BaseModel):
    output: str
    session_id: str
    tools_used: list[str] = []
    tool_traces: list[dict] = []
    history: list[dict] = []


@router.post("/chat", response_model=MCPChatResponse)
def chat(payload: MCPChatRequest, request: Request, _user=Depends(get_current_user)):
    return process_message(payload.message, payload.session_id, request.headers.get("authorization"))


@router.get("/sessions/{session_id}", response_model=MCPChatResponse)
def session_history(session_id: str, _user=Depends(get_current_user)):
    session = sessions.get(session_id)
    return MCPChatResponse(output="", session_id=session_id, history=session.get_history_for_llm())
