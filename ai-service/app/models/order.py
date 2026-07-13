from sqlalchemy import Column, String, Date
from app.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    status_code = Column(String, nullable=False)
    delivery_date = Column(Date, nullable=False)
    
