from app.repositories.policy_repository import PolicyRepository
from app.database import get_db
import json

class PolicyService:

    @staticmethod
    def ask_policy(query: str):
      try:
        repo = PolicyRepository()
        relevant_docs = repo.search_policies(query)
        
        if not relevant_docs:
            return {"message": "No relevant policies found for the given query."}
        
        combined_docs = "\n\n---\n\n".join(relevant_docs)
        
        return {"retrieved_context": combined_docs}
      
      except Exception as e:
        return {"error": f"An error occurred while retrieving policies: {str(e)}"}
