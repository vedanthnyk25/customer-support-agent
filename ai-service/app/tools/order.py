import json
from langchain_core.tools import tool
from langgraph.types import interrupt
from app.services.order_service import OrderService
from app.services.product_service import ProductService


@tool
def order_lookup(order_id: str) -> str:
    """
    Look up an order by its ID.
    """
    order = OrderService.lookup(order_id)
    if not order:
        return json.dumps({"error": f"Order with ID :{order_id} not found"})

    return json.dumps(order)


@tool
def place_order(product_id: str, quantity: int) -> str:
    """
    Place an order for a specific product and quantity.

    ALWAYS call product_lookup first to get the exact product_id and confirm
    the item is in stock -- do not guess a product_id. Only call this tool
    once the user has clearly said they want to buy/order the item (not
    just asked about its price or availability).

    This tool pauses and requires the user to explicitly confirm the order
    (product, quantity, total price) before anything is written to the
    database. Do not ask the user for confirmation yourself in your own
    reply -- the tool's confirmation step handles that; just call the tool
    once you have a product_id and quantity.
    """
    # Re-fetch fresh product info by ID (price/stock may have changed since
    # any earlier product_lookup call, and the LLM may only have a name).
    product = ProductService.get_by_id(product_id)
    if "error" in product:
        return json.dumps(product)

    if product["stock_left"] < quantity:
        return json.dumps({
            "error": f"Only {product['stock_left']} unit(s) of "
                     f"{product['name']} left in stock."
        })

    total_price = round(product["price"] * quantity, 2)

    # Pauses graph execution here. Whatever object is passed in becomes the
    # payload the client (chat.py) forwards to the frontend as a
    # "confirmation_required" event. Whatever the human resumes with
    # (via Command(resume=...)) becomes this call's return value below.
    #
    # IMPORTANT: everything in this function ABOVE this line re-runs from
    # the top when the graph resumes (that's how interrupt() works -- the
    # whole node/tool call is re-executed). Everything above is read-only,
    # so that's safe. The actual write (OrderService.place_order) only
    # happens below, AFTER a confirmed resume -- never before.
    decision = interrupt({
        "type": "order_confirmation",
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "total_price": total_price,
    })

    if not isinstance(decision, dict) or not decision.get("confirmed"):
        return json.dumps({"status": "cancelled", "message": "Order was not placed."})

    result = OrderService.place_order(product_id=product_id, quantity=quantity)
    return json.dumps(result)
