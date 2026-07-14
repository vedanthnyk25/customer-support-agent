from app.database import get_db
from app.repositories.ticket_repository import TicketRepository

class TicketService:
    @staticmethod
    def create(description: str):
        db_session = next(get_db())
        try:
            repo = TicketRepository(db_session)
            ticket_dto = repo.create_ticket(description)
            
            # Convert Pydantic object to a standard dictionary
            return ticket_dto.model_dump()
        finally:
            db_session.close()
