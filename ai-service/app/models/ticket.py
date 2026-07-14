from sqlalchemy import Column, String, Text
from app.database import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    status = Column(String, default="Open")
