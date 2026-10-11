from pydantic import BaseModel, ConfigDict


class InstitutionCreate(BaseModel):
    """Request body for POST /trust/institutions.

    location, established_year and status had no column and now fail with 422
    rather than being dropped.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    # Sent as "institution_type" and stored as institutions.type, because
    # "type" is a builtin and the column is named to avoid shadowing it.
    institution_type: str
    registration_number: str | None = None
    county: str | None = None
    phone: str | None = None
    email: str | None = None
