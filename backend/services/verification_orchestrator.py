import uuid
from datetime import datetime

from repositories.verification_repository import VerificationRepository
from services.question_service import QuestionEngine


class VerificationOrchestrator:

    def __init__(self):

        self.repo = VerificationRepository()
        self.question_service = QuestionEngine()

    def start_session(
        self,
        farmer_id: str
    ):

        session_id = str(uuid.uuid4())

        verification_session = {
            "id": session_id,
            "status": "ACTIVE",
            "created_at": datetime.utcnow().isoformat()
        }

        session = self.repo.create_farmer_session(
            farmer_id,
            verification_session
        )

        trust_sources = (
            self.repo.get_session_trust_sources(
                farmer_id
            )
        )
        from repositories.question_repository import QuestionRepository

        self.question_repo = QuestionRepository()

        for source in trust_sources:

            questions = self.question_service.get_questions(
                source["category"]
            )

            for q in questions:

                question_data = {
                    "id": str(uuid.uuid4()),
                    "source_category": source["category"],
                    "question_code": q["id"],
                    "category": q["category"],
                    "question": q["question"],
                    "weight": q["weight"]
                }

                created = (
                    self.question_repo.create_question(
                        question_data
                    )
                )

                self.repo.attach_question(
                    session_id,
                    created["q"]["id"]
                )

        return {
            "session": dict(session["v"]),
            "participants": [
                dict(source)
                for source in trust_sources
            ]
        }