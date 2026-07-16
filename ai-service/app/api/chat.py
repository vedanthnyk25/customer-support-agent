import json
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessageChunk
from langgraph.types import Command

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()), max_length=200)


class ResumeRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=200)
    confirmed: bool


def _extract_text(content) -> str:
    """Gemini can return content as a plain string OR as a list of parts
    (e.g. [{"type": "text", "text": "..."}]) depending on the chunk.
    Normalize both shapes to a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return ""


async def _stream_agent(agent, graph_input, config):
    """Shared streaming logic used by both a fresh turn (/chat) and a
    resumed post-interrupt turn (/chat/resume).

    Uses two stream modes simultaneously:
      - "messages": token-by-token AIMessageChunk streaming (same behavior
        as before -- one tuple (msg, metadata) per chunk).
      - "updates": lets us detect when the graph has paused on an
        interrupt() call. When that happens, LangGraph's update dict
        contains a "__interrupt__" key holding the Interrupt object(s);
        `.value` is exactly what was passed to interrupt() in the tool
        (see app/tools/order.py). We forward that straight to the client
        instead of the stream just silently going quiet.
    """
    try:
        async for stream_mode, data in agent.astream(
            graph_input, config=config, stream_mode=["messages", "updates"]
        ):
            if stream_mode == "messages":
                msg, _metadata = data
                if not isinstance(msg, AIMessageChunk) or not msg.content:
                    continue
                text = _extract_text(msg.content)
                if text:
                    yield f"data: {json.dumps({'chunk': text})}\n\n"

            elif stream_mode == "updates":
                if isinstance(data, dict) and "__interrupt__" in data:
                    interrupt_obj = data["__interrupt__"][0]
                    yield f"data: {json.dumps({'type': 'confirmation_required', 'payload': interrupt_obj.value})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat_endpoint(request: ChatRequest, http_request: Request):
    thread_id = request.thread_id
    initial_state = {"messages": [HumanMessage(content=request.message)]}
    config = {"configurable": {"thread_id": thread_id}}
    agent = http_request.app.state.agent

    async def response_generator():
        yield f"data: {json.dumps({'thread_id': thread_id})}\n\n"
        async for event in _stream_agent(agent, initial_state, config):
            yield event

    return StreamingResponse(
        response_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/chat/resume")
async def resume_endpoint(request: ResumeRequest, http_request: Request):
    """Resumes a conversation that's paused on a pending confirmation
    (e.g. place_order's HITL interrupt). `confirmed` is whatever the user
    clicked in the frontend's confirmation card."""
    config = {"configurable": {"thread_id": request.thread_id}}
    agent = http_request.app.state.agent

    async def response_generator():
        async for event in _stream_agent(
            agent, Command(resume={"confirmed": request.confirmed}), config
        ):
            yield event

    return StreamingResponse(
        response_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
