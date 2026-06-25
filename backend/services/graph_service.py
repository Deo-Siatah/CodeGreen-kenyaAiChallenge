from repositories.relationship_repositoy import RelationshipRepository


class GraphService:

    def __init__(self):
        self.repository = RelationshipRepository()

    # ==================================================
    # ONBOARDING RELATIONSHIPS
    # ==================================================

    def link_farmer_to_farm(
        self,
        farmer_id: str,
        farm_id: str
    ):
        return self.repository.link_farmer_to_farm(
            farmer_id,
            farm_id
        )

    def link_farmer_to_trust_source(
        self,
        farmer_id: str,
        trust_source_id: str
    ):
        return self.repository.link_farmer_to_trust_source(
            farmer_id,
            trust_source_id
        )

    def link_farmer_to_institution(
        self,
        farmer_id: str,
        institution_id: str
    ):
        return self.repository.link_farmer_to_institution(
            farmer_id,
            institution_id
        )

    def link_farmer_to_social_group(
        self,
        farmer_id: str,
        group_id: str
    ):
        return self.repository.link_farmer_to_social_group(
            farmer_id,
            group_id
        )

    def link_farmer_to_market_actor(
        self,
        farmer_id: str,
        actor_id: str
    ):
        return self.repository.link_farmer_to_market_actor(
            farmer_id,
            actor_id
        )

    # ==================================================
    # TESTIMONIAL RELATIONSHIPS
    # ==================================================

    def trust_source_submits_testimonial(
        self,
        trust_source_id: str,
        testimonial_id: str
    ):
        return self.repository.trust_source_submits_testimonial(
            trust_source_id,
            testimonial_id
        )

    def testimonial_supports_farmer(
        self,
        testimonial_id: str,
        farmer_id: str
    ):
        return self.repository.testimonial_supports_farmer(
            testimonial_id,
            farmer_id
        )

    # ==================================================
    # BUYER TESTIMONIAL RELATIONSHIPS
    # ==================================================

    def market_actor_provides_testimonial(
        self,
        actor_id: str,
        testimonial_id: str
    ):
        return self.repository.market_actor_provides_testimonial(
            actor_id,
            testimonial_id
        )

    def buyer_testimonial_supports_farmer(
        self,
        testimonial_id: str,
        farmer_id: str
    ):
        return self.repository.buyer_testimonial_supports_farmer(
            testimonial_id,
            farmer_id
        )

    # ==================================================
    # IN-KIND SETTLEMENT RELATIONSHIPS
    # ==================================================

    def farmer_provides_settlement(
        self,
        farmer_id: str,
        settlement_id: str
    ):
        return self.repository.farmer_provides_settlement(
            farmer_id,
            settlement_id
        )

    def settlement_validated_by(
        self,
        settlement_id: str,
        trust_source_id: str
    ):
        return self.repository.settlement_validated_by(
            settlement_id,
            trust_source_id
        )

    # ==================================================
    # VERIFICATION SESSION RELATIONSHIPS
    # ==================================================

    def farmer_participates_in_session(
        self,
        farmer_id: str,
        session_id: str
    ):
        return self.repository.farmer_participates_in_session(
            farmer_id,
            session_id
        )

    def session_collects_testimonial(
        self,
        session_id: str,
        testimonial_id: str
    ):
        return self.repository.session_collects_testimonial(
            session_id,
            testimonial_id
        )

    def session_collects_buyer_testimonial(
        self,
        session_id: str,
        testimonial_id: str
    ):
        return self.repository.session_collects_buyer_testimonial(
            session_id,
            testimonial_id
        )

    # ==================================================
    # SCORING RELATIONSHIPS
    # ==================================================

    def farmer_has_signal(
        self,
        farmer_id: str,
        signal_id: str
    ):
        return self.repository.farmer_has_signal(
            farmer_id,
            signal_id
        )

    def signal_contributes_to_score(
        self,
        signal_id: str,
        score_id: str
    ):
        return self.repository.signal_contributes_to_score(
            signal_id,
            score_id
        )

    def farmer_has_score(
        self,
        farmer_id: str,
        score_id: str
    ):
        return self.repository.farmer_has_score(
            farmer_id,
            score_id
        )

    def farmer_received_recommendation(
        self,
        farmer_id: str,
        recommendation_id: str
    ):
        return self.repository.farmer_received_recommendation(
            farmer_id,
            recommendation_id
        )
    
    
    def get_farmer_graph(
    self,
    farmer_id: str
    ):
        return self.repository.get_farmer_graph(
            farmer_id
        )