from app.graph.state import AgentState
from app.services.gemini import get_llm
from app.tools.tool_collection import tools
from app.prompts.system_prompt import system_prompt

def chatbot_node(state: AgentState)->AgentState:
    messages = state.get('messages', [])
    messages.insert(0, system_prompt)
    
    llm = get_llm()
     
    response = llm.invoke(messages)
    
    return {'messages': [response]}
