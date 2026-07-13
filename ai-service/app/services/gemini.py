import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from app.tools.tool_collection import tools

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY is not set in the environment variables.")
    
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key=api_key)

def get_llm():
    return llm.bind_tools(tools)








