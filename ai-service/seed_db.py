from datetime import date, timedelta
from app.database import engine, SessionLocal, Base
from app.models.order import Order
from app.models.product import Product 
from app.models.ticket import Ticket

def seed_database():
    print("Creating database tables...")
    # This creates the tables based on your models (if they don't already exist)
    Base.metadata.create_all(bind=engine)
    
    # Open a database session
    db = SessionLocal()
    
    try:
        # Check for existing data independently
        existing_order = db.query(Order).first()
        existing_product = db.query(Product).first()

        if existing_order and existing_product:
            print("Database already contains both orders and products. Skipping seed.")
            return

        print("Inserting demo data...")
        
        # 1. Seed Orders (if missing)
        if not existing_order:
            demo_orders = [
                Order(
                    id="ORD-001", 
                    status_code="Shipped", 
                    delivery_date=date.today() + timedelta(days=2)
                ),
                Order(
                    id="ORD-002", 
                    status_code="Processing", 
                    delivery_date=date.today() + timedelta(days=5)
                ),
                Order(
                    id="ORD-003", 
                    status_code="Delivered", 
                    delivery_date=date.today() - timedelta(days=1)
                )
            ]
            db.add_all(demo_orders)
            print("Demo orders staged.")

        # 2. Seed Products (if missing)
        if not existing_product:
            demo_products = [
                Product(
                    id="PRD-001",
                    name="Pro Gaming Mouse",
                    description="A high-performance wireless gaming mouse with ultra-low latency.",
                    price=59.99,
                    stock_quantity=12
                ),
                Product(
                    id="PRD-002",
                    name="Elite Ergonomic Mouse",
                    description="Comfortable vertical mouse designed for long hours of productivity.",
                    price=89.99,
                    stock_quantity=5
                ),
                Product(
                    id="PRD-003",
                    name="UltraBook Pro 14",
                    description="Lightweight 14-inch laptop with 16GB RAM and 512GB SSD.",
                    price=799.99,
                    stock_quantity=2
                ),
                Product(
                    id="PRD-004",
                    name="Mechanical Keyboard - Blue Switches",
                    description="Tactile mechanical keyboard with customizable RGB backlighting.",
                    price=119.50,
                    stock_quantity=0  # Out of stock example!
                )
            ]
            db.add_all(demo_products)
            print("Demo products staged.")
        
        # Commit all the staged data to the database
        db.commit()
        print("Successfully seeded the database!")
        
    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
