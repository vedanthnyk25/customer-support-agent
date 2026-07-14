import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY is not set in the environment variables.")

base_llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key=api_key)
base_embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001", api_key=api_key, output_dimensionality=768)

def get_llm():
    from app.tools.tool_collection import tools
    return base_llm.bind_tools(tools)

def get_embeddings():
    return base_embeddings
