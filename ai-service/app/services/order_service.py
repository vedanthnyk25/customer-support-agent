from app.repositories.order_repository import OrderRepository
from app.database import get_db

class OrderService:

    @staticmethod
    def lookup(order_id: str):
        db_session = next(get_db()) 
    
        try:
        # Instantiate layers
            repo = OrderRepository(db_session)
            
            order_data = repo.get_order_by_id(order_id)
            
            return order_data
        finally:
        # Ensure the connection is released back to the pool
            db_session.close()
