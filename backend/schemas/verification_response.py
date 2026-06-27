from pydantic import BaseModel


class VerificationResponseRequest(BaseModel):

    trust_source_id: str
    question_id: str
    answer: str