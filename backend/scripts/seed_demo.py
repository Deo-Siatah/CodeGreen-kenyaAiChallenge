from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urlsplit

from sqlalchemy import delete, select

from core.config import settings
from models.farmer import Farmer
from models.scoring import ScoreProfile
from models.trust import MarketActor, SocialGroup, TrustSource
from repositories.farm_activity_repository import FarmActivityRepository
from services.farmer_service import FarmerService
from services.loan_service import LoanService
from services.trust_service import TrustService
from services.verification_service import VerificationService


@dataclass(frozen=True)
class DemoFarmer:
    name: str
    county: str
    village: str
    gender: str
    farming_type: str
    acreage: float
    latitude: float
    longitude: float
    trust_category: str
    trust_rating: int
    actor_type: str
    buyer_rating: int
    group_name: str
    cycles: int
    settlement_value: float
    capacity: float | None
    loan_amount: int | None = None
    loan_outcome: str | None = None


DEMO_FARMERS: tuple[DemoFarmer, ...] = (
    DemoFarmer(
        "Grace Wanjiku",
        "Nakuru",
        "Bahati",
        "female",
        "horticulture",
        2.4,
        -0.25,
        36.18,
        "Chief",
        4,
        "Buyer",
        4,
        "Umoja Women's Group",
        6,
        5000,
        82,
        loan_amount=5000,
        loan_outcome="repaid",
    ),
    DemoFarmer(
        "Peter Otieno",
        "Kisumu",
        "Ahero",
        "male",
        "maize",
        1.8,
        -0.18,
        34.92,
        "Chief",
        4,
        "Aggregator",
        3,
        "Baraka Savings Group",
        5,
        2000,
        70,
        loan_amount=3000,
        loan_outcome="defaulted",
    ),
    DemoFarmer(
        "Mary Achieng",
        "Siaya",
        "Bondo",
        "female",
        "cassava",
        1.2,
        -0.09,
        34.27,
        "Teacher",
        3,
        "Trader",
        2,
        "Nyabondo Chama",
        3,
        1000,
        55,
    ),
    DemoFarmer(
        "John Kamau",
        "Kiambu",
        "Limuru",
        "male",
        "dairy",
        0.8,
        -1.11,
        36.64,
        "Neighbor",
        2,
        "Trader",
        1,
        "Tumaini Youth Group",
        1,
        200,
        None,
    ),
    DemoFarmer(
        "Esther Muthoni",
        "Meru",
        "Nkubu",
        "female",
        "banana",
        3.1,
        0.07,
        37.65,
        "Cooperative Officer",
        4,
        "Aggregator",
        4,
        "Kithirune Cooperative",
        5,
        3000,
        65,
        loan_amount=5000,
        loan_outcome="disbursed",
    ),
    DemoFarmer(
        "David Kiprop",
        "Uasin Gishu",
        "Kesses",
        "male",
        "maize",
        2.0,
        0.35,
        35.28,
        "Village Elder",
        3,
        "Buyer",
        3,
        "Kesses Farmers Group",
        5,
        1500,
        75,
        loan_amount=3000,
        loan_outcome="pending_disbursement",
    ),
    DemoFarmer(
        "Faith Njeri",
        "Nyeri",
        "Karatina",
        "female",
        "coffee",
        1.5,
        -0.48,
        37.13,
        "Teacher",
        3,
        "Buyer",
        4,
        "Karatina Savings Group",
        5,
        2000,
        72,
    ),
    DemoFarmer(
        "Samuel Ochieng",
        "Kakamega",
        "Mumias",
        "male",
        "sugarcane",
        1.1,
        0.33,
        34.49,
        "Neighbor",
        2,
        "Trader",
        2,
        "Mumias Youth Group",
        2,
        500,
        40,
    ),
)

_TRUST_PHONES = [f"+25479900{i:04d}" for i in range(len(DEMO_FARMERS))]
_ACTOR_PHONES = [f"+25479901{i:04d}" for i in range(len(DEMO_FARMERS))]


def _masked_target() -> str:
    url = urlsplit(settings.DATABASE_URL_POOLED)
    host = url.hostname or "unknown-host"
    database = (url.path or "/").lstrip("/") or "unknown-db"
    return f"{host}/{database}"


async def reset_demo_rows(session) -> None:

    await session.execute(delete(Farmer).where(Farmer.national_id.like("DEMO-%")))
    await session.execute(
        delete(TrustSource).where(TrustSource.national_id.like("DEMO-%"))
    )
    await session.execute(
        delete(MarketActor).where(MarketActor.phone.in_(_ACTOR_PHONES))
    )
    await session.execute(
        delete(SocialGroup).where(
            SocialGroup.name.in_([spec.group_name for spec in DEMO_FARMERS])
        )
    )


async def seed(session) -> None:
    farmers = FarmerService()
    trust = TrustService()
    verification = VerificationService()
    loans = LoanService()
    farm_activity = FarmActivityRepository()

    await reset_demo_rows(session)

    for index, spec in enumerate(DEMO_FARMERS):
        created = await farmers.create_farmer(
            session,
            {
                "full_name": spec.name,
                "national_id": f"DEMO-KE-{index + 1:03d}",
                "phone": f"+25471000{index + 1:04d}",
                "gender": spec.gender,
                "date_of_birth": date.today() - timedelta(days=365 * (28 + index * 3)),
                "location": spec.village,
                "village": spec.village,
                "sub_county": spec.county,
                "county": spec.county,
                "farming_type": spec.farming_type,
                "years_farming": 5 + index,
            },
        )
        farm = await farmers.create_farm(
            session,
            created.id,
            {
                "acreage": spec.acreage,
                "production_type": spec.farming_type,
                "latitude": spec.latitude,
                "longitude": spec.longitude,
            },
        )

        if spec.capacity is not None:
            await farm_activity.create_farm_activity_signal(
                session,
                farm_id=farm.id,
                ndvi_value=0.55 + index * 0.02,
                cultivation_continuity_score=spec.capacity,
                observation_date=date.today(),
                source="sentinel2",
            )

        source = await trust.create_trust_source(
            session,
            {
                "full_name": f"{spec.county} {spec.trust_category}",
                "category": spec.trust_category,
                "phone": _TRUST_PHONES[index],
                "national_id": f"DEMO-TS-{index + 1:03d}",
                "location": spec.county,
            },
        )
        await trust.link_trust_source(
            session,
            created.id,
            source.id,
            relationship_type="community",
            years_known=8,
        )

        actor = await trust.create_market_actor(
            session,
            {
                "name": f"{spec.county} Produce Buyer",
                "actor_type": spec.actor_type,
                "phone": _ACTOR_PHONES[index],
                "location": spec.county,
            },
        )
        await trust.link_market_actor(
            session,
            created.id,
            actor.id,
            relationship_type="buyer",
            since_date=date.today() - timedelta(days=365 * 3),
        )

        group = await trust.create_social_group(
            session,
            {
                "name": spec.group_name,
                "group_type": "Chama",
                "location": spec.county,
                "formation_year": 2016 + index,
            },
        )
        await trust.link_social_group(
            session,
            created.id,
            group.id,
            role="member",
            joined_date=date.today() - timedelta(days=365 * 4),
        )

        await verification.create_settlement(
            session,
            created.id,
            {
                "settlement_type": "produce",
                "estimated_value": spec.settlement_value,
                "verification_status": "verified",
            },
        )

        verification_session = await verification.start_verification(
            session, created.id
        )
        _, participants = await verification.get_session_with_participants(
            session, verification_session.id
        )
        for participant in participants:
            if participant.participant_type == "trust_source":
                payload = {
                    "participant_type": "trust_source",
                    "rating": spec.trust_rating,
                    "comments": "Known in the community for years.",
                    "personal_knowledge_flag": True,
                }
            elif participant.participant_type == "market_actor":
                payload = {
                    "participant_type": "market_actor",
                    "reliability_rating": spec.buyer_rating,
                    "purchase_frequency": "weekly",
                    "relationship_months": 36,
                    "avg_volume_kg": 120.0,
                }
            else:
                payload = {
                    "participant_type": "social_group",
                    "consecutive_cycles": spec.cycles,
                    "last_contribution_date": date.today(),
                    "contribution_amount": 500.0,
                }
            await verification.submit_response(
                session, verification_session.id, participant.id, payload
            )

        profile = (
            await session.execute(
                select(ScoreProfile)
                .where(ScoreProfile.farmer_id == created.id)
                .order_by(ScoreProfile.version.desc())
                .limit(1)
            )
        ).scalars().first()
        if profile is None:
            raise RuntimeError(f"no score profile was produced for {spec.name}")

        if spec.loan_amount is not None and spec.loan_outcome is not None:
            if profile.recommended_amount is None:
                print(
                    f"  ! {spec.name}: score {profile.final_score:.1f} is not eligible; "
                    "skipping the requested loan"
                )
            else:
                amount = min(spec.loan_amount, int(profile.recommended_amount))
                loan = await loans.create_loan(
                    session,
                    created.id,
                    amount,
                    purpose="Farm inputs",
                    duration_months=6,
                    interest_rate=0.0,
                )
                if spec.loan_outcome != "pending_disbursement":
                    await loans.mark_disbursed(session, loan.id)
                if spec.loan_outcome in {"repaid", "defaulted"}:
                    await loans.resolve_loan(session, loan.id, spec.loan_outcome)

        print(
            f"  {spec.name:<16} score={profile.final_score:6.2f} "
            f"{profile.decision:<16} loan={spec.loan_outcome or '-'}"
        )


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan and exit without writing",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm writing to the database named in DATABASE_URL_POOLED",
    )
    args = parser.parse_args()

    print(f"Target: {_masked_target()}")
    print(f"Demo farmers: {len(DEMO_FARMERS)}")
    if args.dry_run:
        for spec in DEMO_FARMERS:
            loan = spec.loan_outcome or "no loan"
            print(f"  {spec.name:<16} {spec.county:<14} loan={loan}")
        print("Dry run - nothing written.")
        return 0
    if not args.yes:
        print(
            "Refusing to write without --yes. Re-run with --dry-run to inspect, "
            "or --yes once you have confirmed the target above."
        )
        return 2

    from core.database import SessionApp, dispose_engines

    try:
        async with SessionApp() as session:
            try:
                await seed(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        print("Seeded demo portfolio.")
        return 0
    finally:
        await dispose_engines()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
