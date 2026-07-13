from app.graph.state import AgentState
from app.services.gemini import get_llm

def Chatbot(state: AgentState)->AgentState:
    messages = state['messages']
    
    response = get_llm.invoke(messages)
    
    return {'messages': [response]}
