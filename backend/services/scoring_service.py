from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.scoring import ScoreComponent, ScoreProfile
from repositories.credibility_repository import CredibilityRepository
from repositories.farm_activity_repository import FarmActivityRepository
from repositories.farmer_repository import FarmerRepository
from repositories.scoring_repository import ScoringRepository
from repositories.signal_repository import SignalRepository
from repositories.trust_repository import TrustRepository
from repositories.verification_repository import VerificationRepository
from services import weighting
from services.audit_service import AuditService


class InsufficientDataError(ValueError):
    """Raised when a farmer has no scoreable signal at all."""


@dataclass(frozen=True)
class ScoreComputationResult:
    profile: ScoreProfile
    components: list[ScoreComponent]
    axis_note: str


class ScoringService:
    """Compute and persist one explainable score in the caller's transaction."""

    def __init__(
        self,
        signal_repository: SignalRepository | None = None,
        credibility_repository: CredibilityRepository | None = None,
        trust_repository: TrustRepository | None = None,
        verification_repository: VerificationRepository | None = None,
        farmer_repository: FarmerRepository | None = None,
        farm_activity_repository: FarmActivityRepository | None = None,
        scoring_repository: ScoringRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.signal_repository = signal_repository or SignalRepository()
        self.credibility_repository = credibility_repository or CredibilityRepository()
        self.trust_repository = trust_repository or TrustRepository()
        self.verification_repository = (
            verification_repository or VerificationRepository()
        )
        self.farmer_repository = farmer_repository or FarmerRepository()
        self.farm_activity_repository = (
            farm_activity_repository or FarmActivityRepository()
        )
        self.scoring_repository = scoring_repository or ScoringRepository()
        self.audit_service = audit_service or AuditService()

    async def compute_score(
        self, session: AsyncSession, farmer_id: uuid.UUID | str
    ) -> ScoreComputationResult:
        signals = await self.signal_repository.get_signals_for_farmer(session, farmer_id)
        components: list[dict[str, Any]] = []
        testimony_entries: list[weighting.TestimonyEntry] = []

        for testimony in signals.testimonials:
            participant = await self.verification_repository.get_participant(
                session, testimony.participant_id
            )
            if participant is None or participant.participant_type != "trust_source":
                continue
            trust_source = await self.trust_repository.get_trust_source(
                session, participant.participant_id
            )
            if trust_source is None:
                continue
            credibility = await self.credibility_repository.get_or_create_credibility(
                session, "trust_source", trust_source.id
            )
            base_weight = weighting.BASE_CATEGORY_WEIGHTS.get(
                trust_source.category, weighting.DEFAULT_UNKNOWN_WEIGHT
            )
            contribution = weighting.testimony_contribution(
                testimony.rating, base_weight, credibility.credibility_score
            )
            testimony_entries.append(
                weighting.TestimonyEntry(
                    contribution, base_weight, trust_source.category
                )
            )
            components.append(
                {
                    "axis": "character",
                    "component_name": "testimony",
                    "raw_value": f"rating={testimony.rating}",
                    "contribution": contribution,
                    "weight": base_weight,
                    "trust_source_id": trust_source.id,
                }
            )

        testimony_score = None
        if testimony_entries:
            pooled = weighting.pool_testimonies(testimony_entries)
            testimony_score = pooled.pooled_score
            pool_id = uuid.uuid4()
            for component in components:
                component["pool_id"] = pool_id
            components.append(
                {
                    "axis": "character",
                    "component_name": "testimony_pool",
                    "raw_value": f"{len(testimony_entries)} testimonies",
                    "contribution": testimony_score,
                    "weight": weighting.TESTIMONY_WEIGHT,
                    "pool_id": pool_id,
                }
            )

        buyer_pool_id = uuid.uuid4()
        buyer_testimony_entries = []
        for row in signals.buyer_testimonials:
            participant = await self.verification_repository.get_participant(
                session, row.participant_id
            )
            if participant is None or participant.participant_type != "market_actor":
                continue
            market_actor = await self.trust_repository.get_market_actor(
                session, participant.participant_id
            )
            if market_actor is None:
                continue
            
            base_weight = weighting.BASE_CATEGORY_WEIGHTS.get(
                market_actor.actor_type, weighting.DEFAULT_UNKNOWN_WEIGHT
            )
            credibility = await self.credibility_repository.get_or_create_credibility(
                session, "market_actor", market_actor.id
            )
            contribution = weighting.testimony_contribution(
                row.reliability_rating, base_weight, credibility.credibility_score
            )
            buyer_testimony_entries.append(
                weighting.TestimonyEntry(
                    contribution, base_weight, market_actor.actor_type
                )
            )
            components.append(
                {
                    "axis": "character",
                    "component_name": "buyer_relationship",
                    "raw_value": f"reliability={row.reliability_rating}",
                    "contribution": contribution,
                    "weight": base_weight,
                    "market_actor_id": market_actor.id,
                }
            )
        
        buyer_score = None
        if buyer_testimony_entries:
            pooled = weighting.pool_testimonies(buyer_testimony_entries)
            buyer_score = pooled.pooled_score
            for component in components:
                if component["component_name"] == "buyer_relationship":
                    component["pool_id"] = buyer_pool_id
            components.append(
                {
                    "axis": "character",
                    "component_name": "buyer_relationship_pool",
                    "raw_value": f"{len(buyer_testimony_entries)} buyer testimonies",
                    "contribution": buyer_score,
                    "weight": weighting.BUYER_WEIGHT,
                    "pool_id": buyer_pool_id,
                }
            )

        discipline_pool_id = uuid.uuid4()
        discipline_contributions = []
        for row in signals.discipline_proxies:
            contribution = weighting.discipline_value(
                row.consecutive_cycles,
                row.last_contribution_date,
                date.today(),
            )
            discipline_contributions.append(contribution)
            components.append(
                {
                    "axis": "character",
                    "component_name": "discipline_proxy",
                    "raw_value": f"{row.consecutive_cycles}_cycles",
                    "contribution": contribution,
                    "weight": weighting.DISCIPLINE_WEIGHT,
                    "pool_id": discipline_pool_id,
                }
            )
        discipline_score = self._append_pool_summary(
            components,
            "discipline_proxy",
            discipline_contributions,
            weighting.DISCIPLINE_WEIGHT,
            discipline_pool_id,
        )

        settlement_pool_id = uuid.uuid4()
        settlement_contributions = []
        for row in signals.settlements:
            contribution = weighting.settlement_value(row.estimated_value)
            settlement_contributions.append(contribution)
            components.append(
                {
                    "axis": "character",
                    "component_name": "in_kind_settlement",
                    "raw_value": f"value={row.estimated_value}",
                    "contribution": contribution,
                    "weight": weighting.SETTLEMENT_WEIGHT,
                    "pool_id": settlement_pool_id,
                }
            )
        settlement_score = self._append_pool_summary(
            components,
            "in_kind_settlement",
            settlement_contributions,
            weighting.SETTLEMENT_WEIGHT,
            settlement_pool_id,
        )

        try:
            character_score = weighting.combine_character_components(
                testimony_score, buyer_score, discipline_score, settlement_score
            )
        except ValueError as exc:
            raise InsufficientDataError(
                f"Farmer {farmer_id} has no scoreable signals"
            ) from exc

        capacity_score = None
        farms = await self.farmer_repository.get_farm_by_farmer_id(session, farmer_id)
        if farms:
            latest = await self.farm_activity_repository.get_latest_for_farm(
                session, farms[0].id
            )
            if latest and latest.cultivation_continuity_score is not None:
                capacity_score = weighting.normalize_capacity_score(
                    latest.cultivation_continuity_score, farms[0].acreage
                )
                components.append(
                    {
                        "axis": "capacity",
                        "component_name": "cultivation_continuity",
                        "raw_value": str(latest.cultivation_continuity_score),
                        "contribution": capacity_score,
                        "weight": weighting.CAPACITY_AXIS_WEIGHT,
                    }
                )

        final_score, axis_note = weighting.combine_axes(character_score, capacity_score)
        decision, recommendation, amount = weighting.apply_decision_thresholds(final_score)
        profile = await self.scoring_repository.create_score_profile(
            session,
            farmer_id,
            character_score=character_score,
            capacity_score=capacity_score,
            final_score=final_score,
            decision=decision,
            recommended_amount=amount,
        )
        rows = list(
            await self.scoring_repository.create_score_components(
                session, profile.id, components
            )
        )
        await self.audit_service.write_log(
            session,
            actor_type="system",
            actor_id=None,
            action="score_computed",
            entity_type="score_profile",
            entity_id=profile.id,
            details={"final_score": final_score, "decision": decision},
        )
        return ScoreComputationResult(profile, rows, axis_note)

    @staticmethod
    def _append_pool_summary(
        components: list[dict[str, Any]],
        component_name: str,
        contributions: list[float],
        weight: float,
        pool_id: uuid.UUID,
    ) -> float | None:
        if not contributions:
            return None
        score = sum(contributions) / len(contributions)
        components.append(
            {
                "axis": "character",
                "component_name": f"{component_name}_pool",
                "raw_value": f"{len(contributions)} entries",
                "contribution": score,
                "weight": weight,
                "pool_id": pool_id,
            }
        )
        return score
