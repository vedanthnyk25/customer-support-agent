import uuid
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.order import Order
from typing import Optional
from pydantic import BaseModel


class OrderDTO(BaseModel):
    id: str
    status_code: str
    delivery_date: str
    product_id: Optional[str] = None
    quantity: Optional[int] = None
    total_price: Optional[float] = None


class OrderRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_order_by_id(self, order_id: str) -> Optional[OrderDTO]:
        order_record = self.db.query(Order).filter(Order.id == order_id).first()

        if not order_record:
            return None

        return OrderDTO(
            id=order_record.id,
            status_code=order_record.status_code,
            delivery_date=str(order_record.delivery_date),
            product_id=order_record.product_id,
            quantity=order_record.quantity,
            total_price=order_record.total_price,
        )

    def create_order(self, product_id: str, quantity: int, total_price: float) -> OrderDTO:
        """Stages a new order in the current session. Deliberately does NOT
        commit -- the service layer commits once, together with the stock
        decrement, so both succeed or both roll back as a single unit."""
        order_id = f"ORD-{str(uuid.uuid4())[:8].upper()}"
        new_order = Order(
            id=order_id,
            status_code="Processing",
            delivery_date=date.today() + timedelta(days=5),
            product_id=product_id,
            quantity=quantity,
            total_price=total_price,
        )
        self.db.add(new_order)
        self.db.flush()  # assigns/validates without committing yet

        return OrderDTO(
            id=new_order.id,
            status_code=new_order.status_code,
            delivery_date=str(new_order.delivery_date),
            product_id=new_order.product_id,
            quantity=new_order.quantity,
            total_price=new_order.total_price,
        )
