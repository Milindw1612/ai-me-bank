"""Ai-ME BANK Agentic AI — FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from a1_msme_credit.router import router as msme_credit_router
from a2_fraud_detection.router import router as fraud_router
from a3_collections_recovery.router import router as collections_router
from shared.config import settings
from shared.database import init_db

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database schema...")
    await init_db()
    logger.info("Ai-ME BANK Agentic AI ready — %s env", settings.app_env)
    yield
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Ai-ME BANK Agentic AI",
    description=(
        "Three production-grade LangGraph use cases:\n"
        "- A1: MSME Credit CAM Prep\n"
        "- A2: Fraud Detection & Investigation\n"
        "- A3: Collections & Delinquency Recovery"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(msme_credit_router)
app.include_router(fraud_router)
app.include_router(collections_router)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.app_port, reload=(settings.app_env == "development"))
