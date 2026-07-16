from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.database import get_db


class OrderService:

    @staticmethod
    def lookup(order_id: str):
        db_session = next(get_db())
        try:
            repo = OrderRepository(db_session)
            order_data = repo.get_order_by_id(order_id)

            if not order_data:
                return {"error": f"Order with ID :{order_id} not found"}

            return order_data.model_dump()
        finally:
            db_session.close()

    @staticmethod
    def place_order(product_id: str, quantity: int):
        """Creates an order and decrements product stock as a single
        atomic transaction. This should only ever be called AFTER a human
        has confirmed the order via the HITL interrupt in the place_order
        tool -- this method itself does not gate on confirmation, it just
        performs the (already-approved) write."""
        db_session = next(get_db())
        try:
            product_repo = ProductRepository(db_session)
            order_repo = OrderRepository(db_session)

            product = product_repo.get_product_by_id(product_id)
            if not product:
                return {"error": f"Product with ID {product_id} not found."}

            if product.stock_left < quantity:
                return {
                    "error": f"Insufficient stock for {product.name}. "
                             f"Only {product.stock_left} left."
                }

            total_price = round(product.price * quantity, 2)

            order = order_repo.create_order(
                product_id=product_id,
                quantity=quantity,
                total_price=total_price,
            )
            product_repo.decrement_stock(product_id, quantity)

            # Single commit: order creation and stock decrement succeed or
            # fail together.
            db_session.commit()

            return order.model_dump()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()
