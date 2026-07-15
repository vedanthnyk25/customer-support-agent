import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.api.chat import router
from app.graph.builder import graph

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

logger = logging.getLogger("uvicorn.error")

DB_STARTUP_TIMEOUT_SECONDS = 10

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set (check that your .env file exists "
            "and is being loaded from the right working directory)."
        )

    logger.info("Connecting to Postgres for checkpointer...")
    try:
        async with asyncio.timeout(DB_STARTUP_TIMEOUT_SECONDS):
            async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
                logger.info("Connected. Running checkpointer.setup()...")
                await checkpointer.setup()
                logger.info("Checkpointer ready. Compiling graph...")
                app.state.agent = graph.compile(checkpointer=checkpointer)
                logger.info("Startup complete.")
                yield
    except TimeoutError:
        raise RuntimeError(
            f"Timed out after {DB_STARTUP_TIMEOUT_SECONDS}s connecting to "
            "Postgres / running checkpointer.setup(). Check that "
            "DATABASE_URL points to a reachable Postgres instance, and "
            "that you are NOT going through a transaction-mode connection "
            "pooler (PgBouncer/Supabase pooler/etc.) -- AsyncPostgresSaver "
            "needs prepared-statement support, which those don't provide "
            "in transaction pooling mode. Use the direct/session connection "
            "string instead."
        )


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(router, prefix="/api")
