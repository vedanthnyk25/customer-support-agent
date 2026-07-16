import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.api.chat import router
from app.graph.builder import graph

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Comma-separated list of allowed frontend origins, e.g.
#   ALLOWED_ORIGINS=http://localhost:3000,https://yourapp.com
# Defaults to localhost:3000 for local dev if not set.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

logger = logging.getLogger("uvicorn.error")

# How long to wait for the DB before giving up and failing loudly instead
# of hanging "Waiting for application startup." forever with no explanation.
DB_STARTUP_TIMEOUT_SECONDS = 10


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set (check that your .env file exists "
            "and is being loaded from the right working directory)."
        )

    # IMPORTANT: build the pool ourselves instead of using
    # AsyncPostgresSaver.from_conn_string(), which creates an unmanaged
    # pool under the hood. psycopg_pool does NOT proactively check
    # whether pooled connections are still alive -- if Postgres (or a
    # managed-DB provider, or a NAT/firewall) closes an idle connection
    # after a while, the pool will still hand it out on the next
    # request, which then fails instantly with "the connection is
    # closed". `check=AsyncConnectionPool.check_connection` validates a
    # connection before handing it out and transparently replaces it if
    # it's dead. `max_idle` proactively recycles idle connections before
    # they're likely to be killed server-side.
    pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=10,
        max_idle=300,       # recycle connections idle > 5 min
        max_lifetime=1800,  # also recycle any connection after 30 min regardless
        check=AsyncConnectionPool.check_connection,
        kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": 0},
        open=False,
    )

    logger.info("Opening Postgres connection pool...")
    try:
        async with asyncio.timeout(DB_STARTUP_TIMEOUT_SECONDS):
            await pool.open()
            checkpointer = AsyncPostgresSaver(pool)
            logger.info("Pool open. Running checkpointer.setup()...")
            await checkpointer.setup()
            logger.info("Checkpointer ready. Compiling graph...")
            app.state.agent = graph.compile(checkpointer=checkpointer)
            logger.info("Startup complete.")
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

    try:
        yield
    finally:
        await pool.close()


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
