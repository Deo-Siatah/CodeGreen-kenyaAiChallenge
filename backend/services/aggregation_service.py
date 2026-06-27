class AggregationService:

    def aggregate(
        self,
        participant_scores: list
    ):

        if not participant_scores:

            return {
                "trust_score": 0,
                "participants": 0
            }

        total_weighted = sum(
            p["weighted_score"]
            for p in participant_scores
        )

        total_weights = sum(
            p["weight"]
            for p in participant_scores
        )

        final_score = (
            total_weighted /
            total_weights
        )

        return {
            "trust_score": round(
                final_score,
                2
            ),
            "participants": len(
                participant_scores
            )
        }