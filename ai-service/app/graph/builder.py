from langgraph.graph import StateGraph, START, END
from app.graph.nodes import Chatbot
from app.graph.state import AgentState

graph = StateGraph(AgentState)

graph.add_node('chatbot', Chatbot)

graph.add_edge(START, 'chatbot')
graph.add_edge('chatbot', END)

agent= graph.compile()

