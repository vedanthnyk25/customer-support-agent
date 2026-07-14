from sqlalchemy.orm import Session
from app.models.product import Product
from typing import List, Dict, Any
from pydantic import BaseModel

class ProductDTO(BaseModel):
    id: str
    name: str
    price: float
    in_stock: bool
    stock_left: int


class ProductRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def search_products(self, search_term: str) -> List[ProductDTO]:
        # Using ilike allows us to find "Mouse" even if the user types "mouse"
        # The % symbols act as wildcards (e.g., matches "Wireless Mouse Pro")
        search_pattern = f"%{search_term}%"
        
        results = self.db.query(Product).filter(
            Product.name.ilike(search_pattern)
        ).limit(5).all() # Limit to 5 so we don't overwhelm the LLM context window
        
        return [
            ProductDTO(
                id=p.id,
                name=p.name,
                price=p.price,
                in_stock=p.stock_quantity > 0,
                stock_left=p.stock_quantity
            )
            for p in results
        ]
