import json
from langchain_core.tools import tool
from app.services.ticket_service import TicketService

@tool
def create_support_ticket(description: str) -> str:
    """
    Create a support ticket when a user wants to file a complaint, report an issue, 
    or escalate a problem. 
    The input 'description' should be a detailed summary of the user's issue.
    """
    result = TicketService.create(description)
    
    return json.dumps(result)
