from core.database import db


def initialize_graph():

    constraints = [

        # Farmer
        """
        CREATE CONSTRAINT farmer_id IF NOT EXISTS
        FOR (f:Farmer)
        REQUIRE f.id IS UNIQUE
        """,

        # Trust Source
        """
        CREATE CONSTRAINT trust_source_id IF NOT EXISTS
        FOR (t:TrustSource)
        REQUIRE t.id IS UNIQUE
        """,

        # Institution
        """
        CREATE CONSTRAINT institution_id IF NOT EXISTS
        FOR (i:Institution)
        REQUIRE i.id IS UNIQUE
        """,

        # Social Group
        """
        CREATE CONSTRAINT social_group_id IF NOT EXISTS
        FOR (g:SocialGroup)
        REQUIRE g.id IS UNIQUE
        """,

        # Market Actor
        """
        CREATE CONSTRAINT market_actor_id IF NOT EXISTS
        FOR (m:MarketActor)
        REQUIRE m.id IS UNIQUE
        """,

        # Farm
        """
        CREATE CONSTRAINT farm_id IF NOT EXISTS
        FOR (f:Farm)
        REQUIRE f.id IS UNIQUE
        """,

        # Loan
        """
        CREATE CONSTRAINT loan_id IF NOT EXISTS
        FOR (l:Loan)
        REQUIRE l.id IS UNIQUE
        """,

        # Verification Session
        """
        CREATE CONSTRAINT verification_session_id IF NOT EXISTS
        FOR (v:VerificationSession)
        REQUIRE v.id IS UNIQUE
        """,

        # Testimonial
        """
        CREATE CONSTRAINT testimonial_id IF NOT EXISTS
        FOR (t:Testimonial)
        REQUIRE t.id IS UNIQUE
        """,

        # Buyer Testimonial
        """
        CREATE CONSTRAINT buyer_testimonial_id IF NOT EXISTS
        FOR (b:BuyerTestimonial)
        REQUIRE b.id IS UNIQUE
        """,

        # In Kind Settlement
        """
        CREATE CONSTRAINT in_kind_settlement_id IF NOT EXISTS
        FOR (i:InKindSettlementProof)
        REQUIRE i.id IS UNIQUE
        """,

        # Financial Signal
        """
        CREATE CONSTRAINT financial_signal_id IF NOT EXISTS
        FOR (f:FinancialSignal)
        REQUIRE f.id IS UNIQUE
        """,

        # Score Profile
        """
        CREATE CONSTRAINT score_profile_id IF NOT EXISTS
        FOR (s:ScoreProfile)
        REQUIRE s.id IS UNIQUE
        """,

        # Recommendation
        """
        CREATE CONSTRAINT recommendation_id IF NOT EXISTS
        FOR (r:Recommendation)
        REQUIRE r.id IS UNIQUE
        """,

        # Notification
        """
        CREATE CONSTRAINT notification_id IF NOT EXISTS
        FOR (n:Notification)
        REQUIRE n.id IS UNIQUE
        """,

        # Evidence
        """
        CREATE CONSTRAINT evidence_id IF NOT EXISTS
        FOR (e:Evidence)
        REQUIRE e.id IS UNIQUE
        """
    ]

    indexes = [

        # Farmer Search
        """
        CREATE INDEX farmer_phone IF NOT EXISTS
        FOR (f:Farmer)
        ON (f.phone)
        """,

        """
        CREATE INDEX farmer_location IF NOT EXISTS
        FOR (f:Farmer)
        ON (f.location)
        """,

        """
        CREATE INDEX farmer_county IF NOT EXISTS
        FOR (f:Farmer)
        ON (f.county)
        """,

        # Trust Source Search
        """
        CREATE INDEX trust_source_category IF NOT EXISTS
        FOR (t:TrustSource)
        ON (t.category)
        """,

        """
        CREATE INDEX trust_source_phone IF NOT EXISTS
        FOR (t:TrustSource)
        ON (t.phone)
        """,

        # Institution Search
        """
        CREATE INDEX institution_type IF NOT EXISTS
        FOR (i:Institution)
        ON (i.institution_type)
        """,

        # Social Group Search
        """
        CREATE INDEX social_group_type IF NOT EXISTS
        FOR (g:SocialGroup)
        ON (g.group_type)
        """,

        # Market Actor Search
        """
        CREATE INDEX market_actor_type IF NOT EXISTS
        FOR (m:MarketActor)
        ON (m.actor_type)
        """,

        # Loan Search
        """
        CREATE INDEX loan_status IF NOT EXISTS
        FOR (l:Loan)
        ON (l.status)
        """,

        # Verification Search
        """
        CREATE INDEX verification_status IF NOT EXISTS
        FOR (v:VerificationSession)
        ON (v.status)
        """,

        # Score Search
        """
        CREATE INDEX score_decision IF NOT EXISTS
        FOR (s:ScoreProfile)
        ON (s.decision)
        """,

        # Evidence Search
        """
        CREATE INDEX evidence_type IF NOT EXISTS
        FOR (e:Evidence)
        ON (e.evidence_type)
        """
    ]

    with db.driver.session() as session:

        for query in constraints:
            session.run(query)

        for query in indexes:
            session.run(query)

    print("Neo4j schema initialized successfully.")