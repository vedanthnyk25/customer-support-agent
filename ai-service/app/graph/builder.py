from langgraph.graph import StateGraph, START, END
from app.graph.nodes import chatbot_node
from app.graph.state import AgentState

graph = StateGraph(AgentState)

graph.add_node('chatbot_node', chatbot_node)

graph.add_edge(START, 'chatbot_node') 
graph.add_edge('chatbot_node', END)

agent= graph.compile()

