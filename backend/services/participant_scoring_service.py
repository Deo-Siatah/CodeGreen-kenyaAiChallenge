class ParticipantScoringService:

    def score_participant(
        self,
        participant_name: str,
        answers: list[str],
        weight: int
    ):

        positive = sum(
            1 for answer in answers
            if answer.upper() == "YES"
        )

        total = len(answers)

        score = (
            positive / total
        ) * 100 if total > 0 else 0

        weighted_score = (
            score * weight
        )

        return {
            "participant": participant_name,
            "score": score,
            "weight": weight,
            "weighted_score": weighted_score
        }