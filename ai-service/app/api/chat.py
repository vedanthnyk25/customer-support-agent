import json
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessageChunk

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000) 
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()), max_length=200)


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


@router.post("/chat")
async def chat_endpoint(request: ChatRequest, http_request: Request):
    user_input = request.message
    thread_id = request.thread_id

    initial_state = {'messages': [HumanMessage(content=user_input)]}
    config = {"configurable": {"thread_id": thread_id}}
    
    agent = http_request.app.state.agent

    async def response_generator():
        yield f"data: {json.dumps({'thread_id': thread_id})}\n\n"

        try:
            async for msg, metadata in agent.astream(
                initial_state, config=config, stream_mode="messages"
            ):
                if not isinstance(msg, AIMessageChunk) or not msg.content:
                    continue

                text = _extract_text(msg.content)
                if text:
                    yield f"data: {json.dumps({'chunk': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        response_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
