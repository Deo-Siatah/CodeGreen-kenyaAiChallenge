from pydantic import BaseModel


class FarmerFarmLink(BaseModel):
    farmer_id: str
    farm_id: str


class FarmerTrustSourceLink(BaseModel):
    farmer_id: str
    trust_source_id: str


class FarmerInstitutionLink(BaseModel):
    farmer_id: str
    institution_id: str


class FarmerSocialGroupLink(BaseModel):
    farmer_id: str
    group_id: str


class FarmerMarketActorLink(BaseModel):
    farmer_id: str
    actor_id: str