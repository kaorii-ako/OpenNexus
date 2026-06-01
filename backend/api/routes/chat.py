from __future__ import annotations
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    cfg = request.app.state.cfg
    engine = request.app.state.engine
    store = request.app.state.store
    session_id = req.session_id or str(uuid.uuid4())
    from backend.agents.chat import chat_once
    response, chunks = await chat_once(req.query, session_id, cfg, engine, store)
    context_chips = [
        {"page_title": c.get("page_title", "?"), "heading": c.get("heading", ""),
         "database": c.get("database", ""), "score": round(c.get("score", 0), 3)}
        for c in chunks
    ]
    return {"response": response, "context_chips": context_chips, "model": engine.model, "session_id": session_id}


@router.get("/chat/stream")
async def chat_stream_endpoint(query: str, request: Request):
    cfg = request.app.state.cfg
    engine = request.app.state.engine
    store = request.app.state.store
    from backend.agents.chat import chat_stream

    async def generate():
        async for token in chat_stream(query, "stream", cfg, engine, store):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
