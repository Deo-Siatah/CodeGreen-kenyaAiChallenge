from typing import Dict, List

from services.weighting_service import WeightingService


class ScoringService:
    """
    Calculates the final trust score once verification is complete.

    This service is intentionally stateless. It does not calculate
    intermediate scores while responses are still coming in.
    """

    def __init__(self, weighting_service: WeightingService):
        self.weighting_service = weighting_service

    def calculate_final_score(self, status: Dict) -> Dict:
        """
        Calculate the final weighted trust score.

        Received participants contribute their weighted score.

        Timeout participants contribute zero while still
        contributing their weighting, penalizing missing
        community verification.
        """

        participant_scores = []

        total_weighted = 0.0
        total_weight = 0.0

        # -------------------------------------------------
        # Score participants that responded
        # -------------------------------------------------

        for participant in status.get("received", []):

            participant_type = participant.get("participant_type")
            participant_name = participant.get("participant_name")

            stored_responses = participant.get("responses", [])

            raw_score = self._calculate_raw_score(
                stored_responses
            )

            weight = self.weighting_service.get_weight(
                participant_type
            )

            weighted_score = raw_score * weight

            participant_scores.append({
                "participant_type": participant_type,
                "participant_name": participant_name,
                "phone": participant.get("participant_phone"),
                "responses": self._format_responses(
                    stored_responses
                ),
                "raw_score": raw_score,
                "weight": weight,
                "weighted_score": round(weighted_score, 2),
                "status": "received"
            })

            total_weighted += weighted_score
            total_weight += weight

        # -------------------------------------------------
        # Timeout participants
        # -------------------------------------------------

        for participant in status.get("timeout", []):

            participant_type = participant.get("participant_type")
            participant_name = participant.get("participant_name")

            weight = self.weighting_service.get_weight(
                participant_type
            )

            participant_scores.append({
                "participant_type": participant_type,
                "participant_name": participant_name,
                "phone": participant.get("participant_phone"),
                "responses": [],
                "raw_score": 0,
                "weight": weight,
                "weighted_score": 0,
                "status": "timeout"
            })

            total_weight += weight

        # -------------------------------------------------
        # Final Trust Score
        # -------------------------------------------------

        if total_weight == 0:
            trust_score = 0.0
        else:
            trust_score = round(
                total_weighted / total_weight,
                2
            )

        decision, recommendation, loan_amount = self._get_decision(
            trust_score,
            len(status.get("timeout", []))
        )

        analysis = self._generate_analysis(
            trust_score,
            participant_scores,
            decision
        )

        return {
            "trust_score": trust_score,
            "decision": decision,
            "recommendation": recommendation,
            "loan_amount_recommended_kes": loan_amount,
            "participant_scores": participant_scores,
            "analysis": analysis
        }

    def calculate_current_score(self, status: Dict) -> float:
        """
        Calculate current intermediate trust score based on received responses.
        Pending participants are excluded, while timeout participants contribute 0 score.
        """
        total_weighted = 0.0
        total_weight = 0.0

        for participant in status.get("received", []):
            participant_type = participant.get("participant_type")
            stored_responses = participant.get("responses", [])
            raw_score = self._calculate_raw_score(stored_responses)
            weight = self.weighting_service.get_weight(participant_type)
            total_weighted += raw_score * weight
            total_weight += weight

        for participant in status.get("timeout", []):
            participant_type = participant.get("participant_type")
            weight = self.weighting_service.get_weight(participant_type)
            total_weight += weight

        if total_weight == 0.0:
            return 0.0
        return round(total_weighted / total_weight, 2)

    # ==========================================================
    # Helpers
    # ==========================================================

    def _calculate_raw_score(
        self,
        responses: List[str]
    ) -> float:
        """
        Calculate score from stored response strings.

        Stored format:

            CH1:YES
            CH2:NO
            CH3:UNSURE
        """

        if not responses:
            return 0.0

        total = 0

        valid = 0

        for response in responses:

            try:
                _, answer = response.split(":", 1)
            except ValueError:
                continue

            valid += 1

            answer = answer.upper()

            if answer == "YES":
                total += 100

            elif answer == "UNSURE":
                total += 50

            else:
                total += 0

        if valid == 0:
            return 0.0

        return round(total / valid, 2)

    def _format_responses(
        self,
        responses: List[str]
    ) -> List[Dict]:
        """
        Convert stored response strings into dictionaries
        expected by the API.

        Example:

        CH1:YES

        becomes

        {
            "question_id": "CH1",
            "answer": "YES"
        }
        """

        formatted = []

        for response in responses:

            try:
                question_id, answer = response.split(":", 1)
            except ValueError:
                continue

            formatted.append({
                "question_id": question_id,
                "answer": answer
            })

        return formatted

    def _get_decision(
        self,
        score: float,
        timeout_count: int
    ):

        if timeout_count > 0:
            return (
                "REVIEW_REQUIRED",
                "Incomplete community verification",
                None
            )

        if score >= 75:
            return (
                "ELIGIBLE",
                "APPROVE_LEVEL_2",
                5000
            )

        if score >= 60:
            return (
                "ELIGIBLE",
                "APPROVE_LEVEL_1",
                3000
            )

        if score >= 45:
            return (
                "REVIEW_REQUIRED",
                "Manual review required",
                None
            )

        return (
            "DECLINE",
            "Insufficient community trust",
            None
        )

    def _generate_analysis(
        self,
        score: float,
        participant_scores: List[Dict],
        decision: str
    ) -> Dict:

        key_drivers = []

        risk_factors = []

        for participant in participant_scores:

            if participant["status"] == "timeout":
                risk_factors.append(
                    f"{participant['participant_type']} did not respond."
                )
                continue

            if participant["raw_score"] >= 75:
                key_drivers.append(
                    f"{participant['participant_type']} ({participant['participant_name']}) provided strong positive verification."
                )

            elif participant["raw_score"] < 50:
                risk_factors.append(
                    f"{participant['participant_type']} provided weak verification."
                )

        if not key_drivers:
            key_drivers.append(
                "No strong positive community endorsements."
            )

        if not risk_factors:
            risk_factors.append(
                "No major verification risks identified."
            )

        if decision == "ELIGIBLE":

            summary = "Strong community verification."

            explanation = (
                f"The farmer achieved a trust score of "
                f"{score:.0f}/100 based on weighted community responses."
            )

        elif decision == "REVIEW_REQUIRED":

            summary = "Manual review recommended."

            explanation = (
                f"The farmer achieved a trust score of "
                f"{score:.0f}/100. Additional review is recommended due "
                f"to incomplete or mixed community verification."
            )

        else:

            summary = "Community verification insufficient."

            explanation = (
                f"The farmer achieved a trust score of "
                f"{score:.0f}/100 which falls below the approval threshold."
            )

        return {
            "summary": summary,
            "explanation": explanation,
            "key_drivers": key_drivers,
            "risk_factors": risk_factors
        }