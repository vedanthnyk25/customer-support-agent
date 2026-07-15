from langchain_core.runnables import RunnableConfig
from app.graph.state import AgentState
from app.services.gemini import get_llm
from app.prompts.system_prompt import system_prompt


async def chatbot_node(state: AgentState, config: RunnableConfig) -> AgentState:
    messages = state.get('messages', [])
    message_with_prompt = [system_prompt] + messages

    llm = get_llm()

    full_response = None
    async for chunk in llm.astream(message_with_prompt, config):
        full_response = chunk if full_response is None else full_response + chunk

    return {'messages': [full_response]}
