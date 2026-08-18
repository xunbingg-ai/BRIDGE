"""Streaming SP chat endpoint (SSE). Frontend integration lands in feat-005."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.llm.client import build_llm_client
from app.services.sp.patient import SPResponder

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStreamRequest(BaseModel):
    case_script: dict
    history: list[dict] = Field(default_factory=list)
    message: str
    language: str = "en"


def get_llm_client(request: Request):
    client = getattr(request.app.state, "llm_client", None)
    if client is None:
        request.app.state.llm_client = build_llm_client()
    return request.app.state.llm_client


@router.post("/stream")
async def chat_stream(request: Request, body: ChatStreamRequest) -> StreamingResponse:
    client = get_llm_client(request)
    responder = SPResponder(client)

    async def event_source():
        async for content in responder.stream_response(
            body.case_script, body.history, body.message, body.language
        ):
            yield f"data: {content}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
