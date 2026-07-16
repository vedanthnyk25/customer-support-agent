from sqlalchemy.orm import Session
from app.models.product import Product
from typing import List, Optional
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
        search_pattern = f"%{search_term}%"

        results = self.db.query(Product).filter(
            Product.name.ilike(search_pattern)
        ).limit(5).all()

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

    def get_product_by_id(self, product_id: str) -> Optional[ProductDTO]:
        p = self.db.query(Product).filter(Product.id == product_id).first()
        if not p:
            return None
        return ProductDTO(
            id=p.id,
            name=p.name,
            price=p.price,
            in_stock=p.stock_quantity > 0,
            stock_left=p.stock_quantity,
        )

    def decrement_stock(self, product_id: str, quantity: int) -> None:
        """Stages the stock decrement in the current session. Does NOT
        commit -- the caller commits this together with order creation."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if product:
            product.stock_quantity = max(product.stock_quantity - quantity, 0)
            self.db.add(product)
