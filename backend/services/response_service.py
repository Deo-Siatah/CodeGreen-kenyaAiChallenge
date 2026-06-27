import uuid
from datetime import datetime

from repositories.response_repository import ResponseRepository
from services.participant_scoring_service import (
    ParticipantScoringService
)

from services.aggregation_service import (
    AggregationService
)


# class ResponseService:

#     def __init__(self):

#         self.repo = ResponseRepository()

#     def submit_response(
#         self,
#         trust_source_id: str,
#         question_id: str,
#         answer: str
#     ):

#         score = 5 if answer.upper() == "YES" else 0

#         response = {
#             "id": str(uuid.uuid4()),
#             "answer": answer,
#             "score": score,
#             "responded_at": datetime.utcnow().isoformat()
#         }

#         created = self.repo.create_response(
#             response
#         )

#         response_id = created["r"]["id"]

#         self.repo.attach_to_question(
#             response_id,
#             question_id
#         )

#         self.repo.attach_to_trust_source(
#             response_id,
#             trust_source_id
#         )

#         return dict(created["r"])

class ResponseService:

    def __init__(self):

        self.participant_scoring_service = (
            ParticipantScoringService()
        )

        self.aggregation_service = (
            AggregationService()
        )

    def simulate_verification(
    self,
    session_id: str
    ):

        participant_scores = []

        participant_scores.append(
            self.participant_scoring_service
            .score_participant(
                "Chief",
                ["YES", "YES", "YES"],
                5
            )
        )

        participant_scores.append(
            self.participant_scoring_service
            .score_participant(
                "Agrovet",
                ["YES", "YES", "NO"],
                4
            )
        )

        participant_scores.append(
            self.participant_scoring_service
            .score_participant(
                "Buyer",
                ["YES", "NO"],
                4
            )
        )

        final_score = (
            self.aggregation_service
            .aggregate(
                participant_scores
            )
        )

        return {
            "session_id": session_id,
            "participant_scores":
                participant_scores,
            "final_result":
                final_score,
            "decision":
                (
                    "ELIGIBLE"
                    if final_score[
                        "trust_score"
                    ] >= 70
                    else "REVIEW_REQUIRED"
                )
        }

