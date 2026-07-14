import uuid
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from pydantic import BaseModel

class TicketDTO(BaseModel):
    id: str
    description: str
    status: str

class TicketRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def create_ticket(self, description: str) -> TicketDTO:
        # Generate a unique 8-character ID like "TKT-A1B2C3D4"
        ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
        
        # Create the database record
        new_ticket = Ticket(
            id=ticket_id, 
            description=description, 
            status="Open"
        )
        
        # Write to the database
        self.db.add(new_ticket)
        self.db.commit()
        self.db.refresh(new_ticket)
        
        # Return the safe Pydantic object
        return TicketDTO(
            id=new_ticket.id,
            description=new_ticket.description,
            status=new_ticket.status
        )
