import json
from langchain_core.tools import tool
from app.services.policy_service import PolicyService

@tool
def policy_lookup(question: str) -> str:
    """
    Search the company knowledge base for official policies, rules, or FAQs.
    Use this when a user asks about returns, refunds, shipping rules, or warranties.
    Pass the user's specific question as the input.
    """
    result = PolicyService.ask_policy(question)
    
    return json.dumps(result)
