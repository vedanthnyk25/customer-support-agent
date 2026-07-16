from sqlalchemy import Column, String, Date, Integer, Float
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    status_code = Column(String, nullable=False)
    delivery_date = Column(Date, nullable=False)
    product_id = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    total_price = Column(Float, nullable=True)
