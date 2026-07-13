from app.graph.state import AgentState
from app.services.gemini import get_llm

def chatbot_node(state: AgentState)->AgentState:
    messages = state.get('messages', [])
    
    llm = get_llm()
    
    response = llm.invoke(messages)
    
    return {'messages': [response]}
