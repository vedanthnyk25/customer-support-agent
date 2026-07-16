from app.database import get_db
from app.repositories.product_repository import ProductRepository


class ProductService:
    @staticmethod
    def search(search_term: str):
        db_session = next(get_db())
        try:
            repo = ProductRepository(db_session)
            products = repo.search_products(search_term)

            if not products:
                return {"message": f"No products found matching '{search_term}'."}

            return {"results": [p.model_dump() for p in products]}
        finally:
            db_session.close()

    @staticmethod
    def get_by_id(product_id: str):
        db_session = next(get_db())
        try:
            repo = ProductRepository(db_session)
            product = repo.get_product_by_id(product_id)
            if not product:
                return {"error": f"Product with ID {product_id} not found."}
            return product.model_dump()
        finally:
            db_session.close()
