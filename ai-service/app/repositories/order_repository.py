from sqlalchemy.orm import Session
from app.models.order import Order
from typing import Dict, Any, Optional

class OrderRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        # Query the database for the order
        order_record = self.db.query(Order).filter(Order.id == order_id).first()
        
        if not order_record:
            return None
            
        # Return it as a dictionary so the Service layer can process it
        return {
            "id": order_record.id,
            "status_code": order_record.status_code,
            "delivery_date": str(order_record.delivery_date)
        }
