import os
from dotenv import load_dotenv
from app.services.gemini import get_embeddings
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore

load_dotenv()


class PolicyRepository:
    def __init__(self):
        self.embeddings = get_embeddings()
        self.index_name = os.getenv("PINECONE_INDEX_NAME")

        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = pc.Index(self.index_name)

        self.vector_store = PineconeVectorStore(
            index=self.index,
            embedding=self.embeddings,
            text_key="text",
        )

    def search_policies(self, query: str, top_k: int = 5) -> list[str]:
        docs = self.vector_store.similarity_search(query, k=top_k)
        return [result.page_content for result in docs]


# Module-level singleton. Building this involves creating an embeddings
# client and opening a connection to a Pinecone index -- expensive to do
# on every single policy lookup
_policy_repository: PolicyRepository | None = None


def get_policy_repository() -> PolicyRepository:
    global _policy_repository
    if _policy_repository is None:
        _policy_repository = PolicyRepository()
    return _policy_repository
