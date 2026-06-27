from fastapi import APIRouter,Form

from services.graph_service import GraphService

from schemas.testimonial import TestimonialCreate
from schemas.buyer_testimonial import BuyerTestimonialCreate
from schemas.inkind_settlement import InKindSettlementProofCreate
from schemas.verify_session import VerificationSessionCreate


router = APIRouter(
    prefix="/verification",
    tags=["Verification"]
)

@router.post("/sessions")
def create_session(
    payload: VerificationSessionCreate
):
    return service.create_verification_session(
        payload.model_dump()
    )

@router.post("/testimonials")
def create_testimonial(
    payload: TestimonialCreate
):
    return service.create_testimonial(
        payload.model_dump()
    )

@router.post("/buyer-testimonials")

def create_buyer_testimonial(
    payload: BuyerTestimonialCreate
):
    return service.create_buyer_testimonial(
        payload.model_dump()
    )

@router.post("/settlement-proofs")
def create_settlement_proof(
    payload: InKindSettlementProofCreate
):
    return service.create_settlement_proof(
        payload.model_dump()
    )


@router.post("/sms")
async def sms_callback(
    from_number: str = Form(...),
    text: str = Form(...)
):
    print("FROM:", from_number)
    print("TEXT:", text)

    return "OK"
service = GraphService()