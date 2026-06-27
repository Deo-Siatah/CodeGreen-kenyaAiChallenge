from typing import Dict

from   services.ai.payload_builder import AIPayloadBuilder
from parsers.parser import GeminiParser

from services.gemini_service import GeminiService


class ExplainabilityService:
    """
    Orchestrates the explainability pipeline.

    Flow:

        Verification Result
                ↓
        Payload Builder
                ↓
            Gemini
                ↓
            Parser
                ↓
      Explainability Response
    """

    def __init__(self):

        self.payload_builder = AIPayloadBuilder()

        self.gemini_service = GeminiService()

        self.parser = GeminiParser()

    def explain(
        self,
        verification_result: Dict
    ) -> Dict:
        """
        Generate AI explanations from the verification result.
        """

        payload = self.payload_builder.build(
            verification_result
        )

        raw_response = self.gemini_service.generate_explanation(
            payload
        )

        parsed_response = self.parser.parse(
            raw_response
        )

        return parsed_response