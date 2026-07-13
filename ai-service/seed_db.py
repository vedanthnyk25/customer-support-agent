from datetime import date, timedelta
from app.database import engine, SessionLocal, Base
from app.models.order import Order

def seed_database():
    print("Creating database tables...")
    # This creates the tables based on your models (if they don't already exist)
    Base.metadata.create_all(bind=engine)
    
    # Open a database session
    db = SessionLocal()
    
    try:
        # Check if we already have data to avoid duplicate errors on multiple runs
        existing_order = db.query(Order).first()
        if existing_order:
            print("Database already contains data. Skipping seed.")
            return

        print("Inserting demo data...")
        
        # Create some mock orders
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
        
        # Add them to the session and commit them to the database
        db.add_all(demo_orders)
        db.commit()
        
        print("Successfully seeded the database with demo orders!")
        
    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
