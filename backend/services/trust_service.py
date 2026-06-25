from repositories.trust_source_repository import TrustSourceRepository
from repositories.socialgroup_repository import SocialGroupRepository
from repositories.institution_repository import InstitutionRepository
from repositories.market_actor_repository import MarketActorRepository
from repositories.buyer_testimonial_repository import BuyerTestimonialRepository
from repositories.settlement_repository import SettlementRepository


class TrustService:

    def __init__(self):
        self.repository = TrustSourceRepository()
        self.social_group_repository = SocialGroupRepository()
        self.institution_repository = InstitutionRepository()
        self.market_actor_repository = MarketActorRepository()
        self.buyer_testimonial_repository = BuyerTestimonialRepository()
        self.settlement_repository = SettlementRepository()

    # Trust Sources

    def create_trust_source(self, data: dict):
        return self.repository.create_trust_source(data)

    # Institutions

    def create_institution(self, data: dict):
        return self.institution_repository.create_institution(data)

    # Social Groups

    def create_social_group(self, data: dict):
        return self.social_group_repository.create_social_group(data)

    # Market Actors

    def create_market_actor(self, data: dict):
        return self.market_actor_repository.create_market_actor(data)

    # Buyer Testimonials

    def create_buyer_testimonial(self, data: dict):
        return self.buyer_testimonial_repository.create_buyer_testimonial(data)

    # In-Kind Settlement Proofs

    def create_settlement_proof(self, data: dict):
        return self.settlement_repository.create_settlement(data)