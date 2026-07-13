import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

get_llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
)






