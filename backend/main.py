from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from core.config import settings, validate_configuration

# Validate before importing core.database: importing that module constructs the
# application engines from settings at module import time.
try:
    validate_configuration()
except Exception as exc:
    logging.getLogger(__name__).error("Application configuration failed: %s", exc)
    raise

from core.database import dispose_engines, verify_db_connection  # noqa: E402
from api.section13 import router as section13_router  # noqa: E402
from api.stats import router as stats_router  # noqa: E402

logger = logging.getLogger(__name__)


def get_farm_activity_provider():
    """Select the configured farm-activity provider at the composition root."""
    if settings.FARM_ACTIVITY_PROVIDER == "earth_engine":
        from services.farm_activity.earth_engine_provider import (
            EarthEngineFarmActivityProvider,
        )

        return EarthEngineFarmActivityProvider()
    from services.farm_activity.provider import NullFarmActivityProvider

    return NullFarmActivityProvider()


def get_explainability_provider():
    """Return the current explanation provider behind a swappable factory."""
    from services.explainability.gemini_provider import GroqExplanationProvider

    return GroqExplanationProvider()


def get_farmer_service():
    from services.farmer_service import FarmerService

    return FarmerService(farm_activity_provider=get_farm_activity_provider())


def get_trust_service():
    from services.trust_service import TrustService

    return TrustService()


def get_verification_service():
    from services.verification_service import VerificationService

    return VerificationService()


def get_loan_service():
    from services.loan_service import LoanService

    return LoanService()


def get_explainability_service():
    from services.explainability.explainability_service import ExplainabilityService

    return ExplainabilityService(get_explainability_provider())


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        validate_configuration()
        # Keep the database health check as the first live dependency check.
        await verify_db_connection()
        # Construct Earth Engine here so invalid credentials fail at startup,
        # not on the first farm creation.
        app.state.farm_activity_provider = get_farm_activity_provider()
    except Exception as exc:
        logger.error("Application startup failed: %s", exc)
        raise RuntimeError(f"Application startup failed: {exc}") from exc

    # TODO(section-5): call verify_scoring_connection() here once app_scoring
    # exists. Deliberately not wired up yet.
    try:
        yield
    finally:
        await dispose_engines()


app = FastAPI(title="Hifadhi API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors as 409 conflicts."""
    logger.error("Database integrity error: %s", str(exc))
    from fastapi import HTTPException
    raise HTTPException(status_code=409, detail="Request conflicts with existing data")


@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint for monitoring and test scripts."""
    return {"status": "ok"}


app.include_router(section13_router)
app.include_router(stats_router)