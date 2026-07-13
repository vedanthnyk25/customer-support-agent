from langgraph.graph import StateGraph
from typing import TypedDict, Annotated
from langgraph.graph.message import BaseMessage, add_messages

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
