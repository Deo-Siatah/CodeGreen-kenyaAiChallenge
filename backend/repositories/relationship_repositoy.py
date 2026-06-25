from repositories.base_repository import BaseRepository


class RelationshipRepository(BaseRepository):

    # -------------------------
    # Farmer → Farm
    # -------------------------

    def link_farmer_to_farm(
        self,
        farmer_id: str,
        farm_id: str
    ):

        query = """
        MATCH (f:Farmer {id:$farmer_id})
        MATCH (farm:Farm {id:$farm_id})

        MERGE (f)-[:OWNS]->(farm)

        RETURN f, farm
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id,
                farm_id=farm_id
            ).single()

    # -------------------------
    # Farmer → Trust Source
    # -------------------------

    def link_farmer_to_trust_source(
        self,
        farmer_id: str,
        trust_source_id: str
    ):

        query = """
        MATCH (f:Farmer {id:$farmer_id})
        MATCH (t:TrustSource {id:$trust_source_id})

        MERGE (f)-[:VERIFIED_BY]->(t)

        RETURN f, t
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id,
                trust_source_id=trust_source_id
            ).single()

    # -------------------------
    # Farmer → Institution
    # -------------------------

    def link_farmer_to_institution(
        self,
        farmer_id: str,
        institution_id: str
    ):

        query = """
        MATCH (f:Farmer {id:$farmer_id})
        MATCH (i:Institution {id:$institution_id})

        MERGE (f)-[:MEMBER_OF]->(i)

        RETURN f, i
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id,
                institution_id=institution_id
            ).single()

    # -------------------------
    # Farmer → Social Group
    # -------------------------

    def link_farmer_to_social_group(
        self,
        farmer_id: str,
        group_id: str
    ):

        query = """
        MATCH (f:Farmer {id:$farmer_id})
        MATCH (g:SocialGroup {id:$group_id})

        MERGE (f)-[:MEMBER_OF]->(g)

        RETURN f, g
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id,
                group_id=group_id
            ).single()

    # -------------------------
    # Farmer → Market Actor
    # -------------------------

    def link_farmer_to_market_actor(
        self,
        farmer_id: str,
        actor_id: str
    ):

        query = """
        MATCH (f:Farmer {id:$farmer_id})
        MATCH (m:MarketActor {id:$actor_id})

        MERGE (f)-[:SELLS_TO]->(m)

        RETURN f, m
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id,
                actor_id=actor_id
            ).single()
    
    #### Verification Relationships   

    # -------------------------
    # Truct source submits testimonial for farmer
    # -------------------------
    def trust_source_submits_testimonial(
    self,
    trust_source_id: str,
    testimonial_id: str
    ):

        query = """
        MATCH (t:TrustSource {id:$trust_source_id})
        MATCH (test:Testimonial {id:$testimonial_id})

        MERGE (t)-[:SUBMITTED]->(test)

        RETURN t, test
        """

        with self.driver.session() as session:
            return session.run(
                query,
                trust_source_id=trust_source_id,
                testimonial_id=testimonial_id
            ).single()
    
    # -------------------------
    # Testimonial supports farmer
    # -------------------------
    def testimonial_supports_farmer(
    self,
    testimonial_id: str,
    farmer_id: str
    ):

        query = """
        MATCH (t:Testimonial {id:$testimonial_id})
        MATCH (f:Farmer {id:$farmer_id})

        MERGE (t)-[:SUPPORTS]->(f)

        RETURN t, f
        """

        with self.driver.session() as session:
            return session.run(
                query,
                testimonial_id=testimonial_id,
                farmer_id=farmer_id
            ).single()


    ### Buyer Testimonial Relationships 
    # -------------------------
    # Market Actor provides buyer testimonial
    # -------------------------

    def market_actor_provides_testimonial(
    self,
    actor_id: str,
    testimonial_id: str
    ):

        query = """
        MATCH (m:MarketActor {id:$actor_id})
        MATCH (b:BuyerTestimonial {id:$testimonial_id})

        MERGE (m)-[:PROVIDED]->(b)

        RETURN m, b
        """

        with self.driver.session() as session:
            return session.run(
                query,
                actor_id=actor_id,
                testimonial_id=testimonial_id
            ).single()
    
    # -------------------------
    # Buyer Testimonial supports farmer
    # -------------------------

    def buyer_testimonial_supports_farmer(
    self,
    testimonial_id: str,
    farmer_id: str
    ):

        query = """
        MATCH (b:BuyerTestimonial {id:$testimonial_id})
        MATCH (f:Farmer {id:$farmer_id})

        MERGE (b)-[:SUPPORTS]->(f)

        RETURN b, f
        """

        with self.driver.session() as session:
            return session.run(
                query,
                testimonial_id=testimonial_id,
                farmer_id=farmer_id
            ).single()

    

    ### In-Kind Settlement Relationships
    # -------------------------
    # Farmer provides settlement proof
    # -------------------------
    def farmer_provides_settlement(
    self,
    farmer_id: str,
    settlement_id: str
    ):

        query = """
        MATCH (f:Farmer {id:$farmer_id})
        MATCH (s:InKindSettlementProof {id:$settlement_id})

        MERGE (f)-[:PROVIDED]->(s)

        RETURN f, s
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id,
                settlement_id=settlement_id
            ).single()
    ##Trust Source validates settlement proof
        
    def settlement_validated_by(
    self,
    settlement_id: str,
    trust_source_id: str
    ):

        query = """
        MATCH (s:InKindSettlementProof {id:$settlement_id})
        MATCH (t:TrustSource {id:$trust_source_id})

        MERGE (s)-[:VALIDATED_BY]->(t)

        RETURN s, t
        """

        with self.driver.session() as session:
            return session.run(
                query,
                settlement_id=settlement_id,
                trust_source_id=trust_source_id
            ).single()
        
    
    # -------------------------
    # Verification Session Relationships
    # -------------------------
    def farmer_participates_in_session(
    self,
    farmer_id: str,
    session_id: str
    ):
        query = """
        MATCH (f:Farmer {id:$farmer_id})
        MATCH (v:VerificationSession {id:$session_id})

        MERGE (f)-[:PARTICIPATED_IN]->(v)

        RETURN f, v
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id,
                session_id=session_id
            ).single()
        
    
    def session_collects_testimonial(
    self,
    session_id: str,
    testimonial_id: str
    ):
        query = """
        MATCH (v:VerificationSession {id:$session_id})
        MATCH (t:Testimonial {id:$testimonial_id})

        MERGE (v)-[:COLLECTED]->(t)

        RETURN v, t
        """

        with self.driver.session() as session:
            return session.run(
                query,
                session_id=session_id,
                testimonial_id=testimonial_id
            ).single()
        
    # -------------------------
    # Scoring Relationship
    # -------------------------

    def farmer_has_signal(
    self,
    farmer_id: str,
    signal_id: str
    ):
        query = """
        MATCH (f:Farmer {id:$farmer_id})
        MATCH (s:FinancialSignal {id:$signal_id})

        MERGE (f)-[:HAS_SIGNAL]->(s)

        RETURN f, s
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id,
                signal_id=signal_id
            ).single()
        
    def signal_contributes_to_score(
    self,
    signal_id: str,
    score_id: str
    ):
        query = """
        MATCH (s:FinancialSignal {id:$signal_id})
        MATCH (sp:FinancialScore {id:$score_id})

        MERGE (s)-[:CONTRIBUTES_TO]->(sp)

        RETURN s, sp
        """

        with self.driver.session() as session:
            return session.run(
                query,
                signal_id=signal_id,
                score_id=score_id
            ).single()
        
    def farmer_has_score(
    self,
    farmer_id: str,
    score_id: str
    ):
        query = """
        MATCH (f:Farmer {id:$farmer_id})
        MATCH (sp:ScoreProfile {id:$score_id})

        MERGE (f)-[:HAS_SCORE]->(sp)

        RETURN f, sp
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id,
                score_id=score_id
            ).single()
        
    def farmer_received_recommendation(
    self,
    farmer_id: str,
    recommendation_id: str
    ):
        query = """
        MATCH (f:Farmer {id:$farmer_id})
        MATCH (r:Recommendation {id:$recommendation_id})

        MERGE (f)-[:RECEIVED]->(r)

        RETURN f, r
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id,
                recommendation_id=recommendation_id
            ).single()
        
    ## graph retrival method
    def get_farmer_graph(
    self,
    farmer_id: str
    ):
        query = """
        MATCH (f:Farmer {id:$farmer_id})
        OPTIONAL MATCH (f)-[r]-(n)
        RETURN f,
            collect(DISTINCT r) as relationships,
            collect(DISTINCT n) as connected_nodes
        """

        with self.driver.session() as session:
            return session.run(
                query,
                farmer_id=farmer_id
            ).single()