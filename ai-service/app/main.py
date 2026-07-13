from fastapi import FastAPI
from app.api.chat import router

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(router, prefix="/api")
