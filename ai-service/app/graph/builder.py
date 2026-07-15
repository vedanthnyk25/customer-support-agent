from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.graph.nodes import chatbot_node
from app.graph.state import AgentState
from app.tools.tool_collection import tools

graph = StateGraph(AgentState)

graph.add_node('chatbot_node', chatbot_node)
graph.add_node('tools', ToolNode(tools))

graph.add_edge(START, 'chatbot_node')
graph.add_conditional_edges('chatbot_node', tools_condition)
graph.add_edge('tools', 'chatbot_node') 

