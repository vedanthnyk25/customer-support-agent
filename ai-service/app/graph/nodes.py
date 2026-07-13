from app.graph.state import AgentState
from app.services.gemini import get_llm
from app.tools.tool_collection import tools

def chatbot_node(state: AgentState)->AgentState:
    messages = state.get('messages', [])
    llm = get_llm()
     
    response = llm.invoke(messages)
    
    return {'messages': [response]}
