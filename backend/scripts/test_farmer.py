from uuid import uuid4

from core.database import db


def seed_graph():

    with db.driver.session() as session:

        print("Clearing existing graph...")

        session.run("""
        MATCH (n)
        DETACH DELETE n
        """)

        print("Creating Farmers...")

        session.run("""
        CREATE
        (f1:Farmer {
            id:$f1,
            full_name:'John Kamau',
            age:34,
            gender:'Male',
            phone:'0712345678',
            location:'Kirinyaga',
            farming_type:'Banana Farming'
        }),
        (f2:Farmer {
            id:$f2,
            full_name:'Mary Wanjiku',
            age:41,
            gender:'Female',
            phone:'0722334455',
            location:'Nyeri',
            farming_type:'Dairy Farming'
        }),
        (f3:Farmer {
            id:$f3,
            full_name:'Peter Mwangi',
            age:29,
            gender:'Male',
            phone:'0733445566',
            location:'Meru',
            farming_type:'Maize Farming'
        }),
        (f4:Farmer {
            id:$f4,
            full_name:'Grace Atieno',
            age:38,
            gender:'Female',
            phone:'0744556677',
            location:'Kisumu',
            farming_type:'Poultry Farming'
        }),
        (f5:Farmer {
            id:$f5,
            full_name:'James Kiptoo',
            age:45,
            gender:'Male',
            phone:'0755667788',
            location:'Eldoret',
            farming_type:'Mixed Farming'
        })
        """,
        f1=str(uuid4()),
        f2=str(uuid4()),
        f3=str(uuid4()),
        f4=str(uuid4()),
        f5=str(uuid4())
        )

        print("Creating Farms...")

        session.run("""
        CREATE
        (farm1:Farm {
            id:'farm-1',
            acreage:2,
            primary_crop:'Bananas',
            production_type:'Crop'
        }),
        (farm2:Farm {
            id:'farm-2',
            acreage:5,
            primary_crop:'Dairy',
            production_type:'Livestock'
        }),
        (farm3:Farm {
            id:'farm-3',
            acreage:3,
            primary_crop:'Maize',
            production_type:'Crop'
        }),
        (farm4:Farm {
            id:'farm-4',
            acreage:1,
            primary_crop:'Poultry',
            production_type:'Livestock'
        }),
        (farm5:Farm {
            id:'farm-5',
            acreage:4,
            primary_crop:'Mixed',
            production_type:'Mixed'
        })
        """)

        print("Creating Trust Sources...")

        session.run("""
        CREATE
        (chief:TrustSource {
            id:'ts-1',
            name:'Chief Njoroge',
            category:'Chief',
            credibility_score:95
        }),

        (elder:TrustSource {
            id:'ts-2',
            name:'Mzee Kariuki',
            category:'Village Elder',
            credibility_score:88
        }),

        (teacher:TrustSource {
            id:'ts-3',
            name:'Mr Mutiso',
            category:'Teacher',
            credibility_score:85
        }),

        (agrovet:TrustSource {
            id:'ts-4',
            name:'Green Agrovet',
            category:'Agrovet Owner',
            credibility_score:90
        }),

        (health:TrustSource {
            id:'ts-5',
            name:'Nurse Atieno',
            category:'Health Worker',
            credibility_score:82
        })
        """)

        print("Creating Institutions...")

        session.run("""
        CREATE
        (sacco:Institution {
            id:'inst-1',
            name:'Mwea SACCO',
            institution_type:'SACCO'
        }),

        (coop:Institution {
            id:'inst-2',
            name:'Kirinyaga Cooperative',
            institution_type:'Cooperative'
        }),

        (school:Institution {
            id:'inst-3',
            name:'St Mary School',
            institution_type:'School'
        })
        """)

        print("Creating Social Groups...")

        session.run("""
        CREATE
        (chama:SocialGroup {
            id:'group-1',
            name:'Women Chama',
            group_type:'Savings Group'
        }),

        (youth:SocialGroup {
            id:'group-2',
            name:'Youth Farmers',
            group_type:'Youth Group'
        }),

        (banana:SocialGroup {
            id:'group-3',
            name:'Banana Producers',
            group_type:'Producer Group'
        })
        """)

        print("Creating Market Actors...")

        session.run("""
        CREATE
        (buyer1:MarketActor {
            id:'market-1',
            name:'Banana Aggregator',
            actor_type:'Aggregator'
        }),

        (buyer2:MarketActor {
            id:'market-2',
            name:'Milk Collection Center',
            actor_type:'Buyer'
        }),

        (buyer3:MarketActor {
            id:'market-3',
            name:'Produce Trader',
            actor_type:'Trader'
        })
        """)

        print("Creating Financial Signals...")

        session.run("""
        CREATE
        (s1:FinancialSignal {
            id:'signal-1',
            signal_type:'M-Pesa Activity',
            score:80
        }),

        (s2:FinancialSignal {
            id:'signal-2',
            signal_type:'Utility Payments',
            score:70
        }),

        (s3:FinancialSignal {
            id:'signal-3',
            signal_type:'Savings Activity',
            score:90
        }),

        (s4:FinancialSignal {
            id:'signal-4',
            signal_type:'Cooperative Deliveries',
            score:75
        }),

        (s5:FinancialSignal {
            id:'signal-5',
            signal_type:'Previous Loan Record',
            score:85
        })
        """)

        print("Creating Score Profiles...")

        session.run("""
        CREATE
        (sp1:ScoreProfile {
            id:'score-1',
            total_score:82
        }),

        (sp2:ScoreProfile {
            id:'score-2',
            total_score:76
        }),

        (sp3:ScoreProfile {
            id:'score-3',
            total_score:68
        }),

        (sp4:ScoreProfile {
            id:'score-4',
            total_score:59
        }),

        (sp5:ScoreProfile {
            id:'score-5',
            total_score:87
        })
        """)

        print("Creating Relationships...")

        session.run("""

        MATCH (f1:Farmer {full_name:'John Kamau'})
        MATCH (f2:Farmer {full_name:'Mary Wanjiku'})
        MATCH (f3:Farmer {full_name:'Peter Mwangi'})
        MATCH (f4:Farmer {full_name:'Grace Atieno'})
        MATCH (f5:Farmer {full_name:'James Kiptoo'})

        MATCH (farm1:Farm {id:'farm-1'})
        MATCH (farm2:Farm {id:'farm-2'})
        MATCH (farm3:Farm {id:'farm-3'})
        MATCH (farm4:Farm {id:'farm-4'})
        MATCH (farm5:Farm {id:'farm-5'})

        MATCH (chief:TrustSource {category:'Chief'})
        MATCH (elder:TrustSource {category:'Village Elder'})
        MATCH (teacher:TrustSource {category:'Teacher'})
        MATCH (agrovet:TrustSource {category:'Agrovet Owner'})
        MATCH (health:TrustSource {category:'Health Worker'})

        MATCH (sacco:Institution {institution_type:'SACCO'})
        MATCH (coop:Institution {institution_type:'Cooperative'})

        MATCH (chama:SocialGroup {id:'group-1'})
        MATCH (youth:SocialGroup {id:'group-2'})
        MATCH (banana:SocialGroup {id:'group-3'})

        MATCH (buyer1:MarketActor {id:'market-1'})
        MATCH (buyer2:MarketActor {id:'market-2'})
        MATCH (buyer3:MarketActor {id:'market-3'})

        MATCH (signal1:FinancialSignal {id:'signal-1'})
        MATCH (signal2:FinancialSignal {id:'signal-2'})
        MATCH (signal3:FinancialSignal {id:'signal-3'})
        MATCH (signal4:FinancialSignal {id:'signal-4'})
        MATCH (signal5:FinancialSignal {id:'signal-5'})

        MATCH (sp1:ScoreProfile {id:'score-1'})
        MATCH (sp2:ScoreProfile {id:'score-2'})
        MATCH (sp3:ScoreProfile {id:'score-3'})
        MATCH (sp4:ScoreProfile {id:'score-4'})
        MATCH (sp5:ScoreProfile {id:'score-5'})

        CREATE (f1)-[:OWNS]->(farm1)
        CREATE (f2)-[:OWNS]->(farm2)
        CREATE (f3)-[:OWNS]->(farm3)
        CREATE (f4)-[:OWNS]->(farm4)
        CREATE (f5)-[:OWNS]->(farm5)

        CREATE (f1)-[:VERIFIED_BY]->(chief)
        CREATE (f1)-[:VERIFIED_BY]->(agrovet)

        CREATE (f2)-[:VERIFIED_BY]->(elder)
        CREATE (f2)-[:VERIFIED_BY]->(teacher)

        CREATE (f3)-[:VERIFIED_BY]->(chief)

        CREATE (f1)-[:MEMBER_OF]->(sacco)
        CREATE (f2)-[:MEMBER_OF]->(coop)

        CREATE (f1)-[:MEMBER_OF]->(banana)
        CREATE (f2)-[:MEMBER_OF]->(chama)
        CREATE (f3)-[:MEMBER_OF]->(youth)

        CREATE (f1)-[:SELLS_TO]->(buyer1)
        CREATE (f2)-[:SELLS_TO]->(buyer2)
        CREATE (f3)-[:SELLS_TO]->(buyer3)

        CREATE (f1)-[:HAS_SIGNAL]->(signal1)
        CREATE (f2)-[:HAS_SIGNAL]->(signal2)
        CREATE (f3)-[:HAS_SIGNAL]->(signal3)
        CREATE (f4)-[:HAS_SIGNAL]->(signal4)
        CREATE (f5)-[:HAS_SIGNAL]->(signal5)

        CREATE (f1)-[:HAS_SCORE]->(sp1)
        CREATE (f2)-[:HAS_SCORE]->(sp2)
        CREATE (f3)-[:HAS_SCORE]->(sp3)
        CREATE (f4)-[:HAS_SCORE]->(sp4)
        CREATE (f5)-[:HAS_SCORE]->(sp5)

        """)

        print("Graph seeded successfully!")


if __name__ == "__main__":
    seed_graph()