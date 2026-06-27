from services.weighting_service import WeightingService


class TrustScoringService:

    ANSWER_VALUES = {
        "YES": 100,
        "NO": 0
    }

    def __init__(self):

        self.weighting_service = WeightingService()

    def calculate_participant_score(
        self,
        category: str,
        responses: list[str]
    ):

        scores = []

        for response in responses:

            score = self.ANSWER_VALUES.get(
                response.upper(),
                0
            )

            scores.append(score)

        if not scores:
            return {
                "raw_score": 0,
                "weighted_score": 0
            }

        raw_score = sum(scores) / len(scores)

        weight = self.weighting_service.get_weight(
            category
        )

        weighted_score = raw_score * weight

        return {
            "raw_score": round(raw_score, 2),
            "weight": weight,
            "weighted_score": round(weighted_score, 2)
        }