from pydantic import BaseModel, ConfigDict


class TrustSourceCreate(BaseModel):
    """Request body for POST /trust/sources.

    extra="forbid" so a client cannot send a field that silently does nothing.
    The fields that used to live here and have no column behind them
    (gender, institution_name, years_known_farmer, credibility_score,
    verification_count, successful_verifications, failed_verifications, status)
    now fail with 422 instead of being dropped on the floor. credibility_score
    in particular is derived from repayment history by CredibilityRepository,
    so accepting it from a client would create a second source of truth.
    """

    model_config = ConfigDict(extra="forbid")

    # Sent as "name" and stored as trust_sources.full_name.
    name: str
    category: str
    phone: str | None = None
    national_id: str | None = None
    location: str
