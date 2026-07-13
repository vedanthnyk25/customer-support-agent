from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.graph.builder import agent
from langchain_core.messages import HumanMessage

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    
    user_input = request.message
    # Here you would typically call your chat model or service
    # For demonstration, we'll just echo the user input
    initial_state= {
    'messages': [HumanMessage(content= user_input)]
}
    chat_response = agent.invoke(initial_state)
        
    response_content = chat_response['messages'][-1].content[0]['text']

    return {"response": response_content}
