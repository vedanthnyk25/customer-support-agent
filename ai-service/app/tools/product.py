import json
from langchain_core.tools import tool
from app.services.product_service import ProductService

@tool
def product_lookup(search_term: str) -> str:
    """
    Search for a product by its name or a keyword (e.g., 'mouse', 'laptop', 'keyboard').
    Use this when a user asks about product availability, price, or details.
    """
    # Example: If the user asks "How much is the wireless mouse?", 
    # the LLM will intelligently extract "wireless mouse" as the search_term.
    
    result = ProductService.search(search_term)
    
    return json.dumps(result)
