from fastapi import APIRouter

from services.farmer_service import FarmerService
from schemas.farmer import FarmerCreate

router = APIRouter(
    prefix="/farmers",
    tags=["Farmers"]
)

service = FarmerService()


@router.post("")
def create_farmer(payload: FarmerCreate):
    return service.create_farmer(payload.model_dump())


@router.get("/{farmer_id}")
def get_farmer(farmer_id: str):
    return service.get_farmer(farmer_id)


@router.get("")
def list_farmers():
    return service.list_farmers()