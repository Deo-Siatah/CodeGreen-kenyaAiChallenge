from fastapi import APIRouter

from services.graph_service import GraphService

from schemas.relationship import (
    FarmerFarmLink,
    FarmerTrustSourceLink,
    FarmerInstitutionLink,
    FarmerSocialGroupLink,
    FarmerMarketActorLink,
)

router = APIRouter(
    prefix="/relationships",
    tags=["Relationships"]
)

@router.post("/farmer-farm")
def link_farmer_farm(
    payload: FarmerFarmLink
):
    return service.link_farmer_to_farm(
        payload.farmer_id,
        payload.farm_id
    )

@router.post("/farmer-trust-source")
def link_farmer_trust_source(
    payload: FarmerTrustSourceLink
):
    return service.link_farmer_to_trust_source(
        payload.farmer_id,
        payload.trust_source_id
    )

@router.post("/farmer-institution")
def link_farmer_institution(
    payload: FarmerInstitutionLink
):
    return service.link_farmer_to_institution(
        payload.farmer_id,
        payload.institution_id
    )

@router.post("/farmer-social-group")
def link_farmer_social_group(
    payload: FarmerSocialGroupLink
):
    return service.link_farmer_to_social_group(
        payload.farmer_id,
        payload.group_id
    )

@router.post("/farmer-market-actor")
def link_farmer_market_actor(
    payload: FarmerMarketActorLink
):
    return service.link_farmer_to_market_actor(
        payload.farmer_id,
        payload.actor_id
    )



##retrieval endpoint
@router.get("/graph/{farmer_id}")
def get_farmer_graph(
    farmer_id: str
):
    return service.get_farmer_graph(
        farmer_id
    )
service = GraphService()