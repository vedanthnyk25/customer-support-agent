from langchain_core.tools import tool
import json
from app.services.order_service import OrderService

@tool
def order_lookup(order_id: str) -> str:
    """
    Look up an order by its ID.
    """
    
    order= OrderService.lookup(order_id)
    if not order:
        return json.dumps({"error": f"Order with ID :{order_id} not found"})
    
    return order



