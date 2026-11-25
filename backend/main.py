import logging
from contextlib import asynccontextmanager
import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from database import check_database, initialize_database
from users import router as users_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Users API",
    lifespan=lifespan,
)

app.include_router(users_router)


@app.get("/health/live")
def health_live():
    return {"status": "alive"}


@app.get("/health")
def health_ready():
    try:
        check_database()
    except psycopg.Error:
        logger.warning("Database readiness check failed")

        return JSONResponse(
            status_code=503,
            content={"status": "not_ready"},
        )

    return {"status": "ready"}


@app.exception_handler(psycopg.Error)
async def database_error(
    request: Request,
    exc: psycopg.Error,
):
    logger.error(
        "Database request failed",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    if isinstance(
        exc,
        (psycopg.OperationalError, psycopg.InterfaceError),
    ):
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "DATABASE_UNAVAILABLE",
                    "message": (
                        "The database operation could not be completed."
                    ),
                }
            },
        )
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "DATABASE_ERROR",
                "message": "An unexpected database error occurred.",
            }
        },
    )
