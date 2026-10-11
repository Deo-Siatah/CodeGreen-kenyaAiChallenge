from pydantic import BaseModel, ConfigDict


class SocialGroupCreate(BaseModel):
    """Request body for POST /trust/social-groups.

    member_count, savings_frequency, average_contribution, credibility_score and
    status had no column and now fail with 422 rather than being dropped.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    group_type: str
    location: str
    formation_year: int | None = None
