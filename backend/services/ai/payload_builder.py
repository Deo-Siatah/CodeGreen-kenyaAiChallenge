from typing import Dict, List


class AIPayloadBuilder:
    """
    Builds a privacy-safe payload for Gemini.

    Raw participant identities are removed before
    sending any information to the LLM.
    """

    def build(self, verification_result: Dict) -> Dict:

        participant_summary = []

        for participant in verification_result.get(
            "participant_scores",
            []
        ):

            participant_summary.append({
                "participant_type": participant["participant_type"],
                "score": participant["raw_score"],
                "response_count": len(
                    participant.get("responses", [])
                )
            })

        return {

            "trust_score":
                verification_result["trust_score"],

            "decision":
                verification_result["decision"],

            "recommendation":
                verification_result["recommendation"],

            "loan_amount":
                verification_result[
                    "loan_amount_recommended_kes"
                ],

            "participants":
                participant_summary,

            "analysis":
                verification_result["analysis"]
        }