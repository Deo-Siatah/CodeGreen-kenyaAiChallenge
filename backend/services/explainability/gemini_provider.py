# """Gemini explanation provider with an explicit PII boundary."""

# from __future__ import annotations

# import re
# from typing import Any, Literal

# from google import  genai
# from google.genai import types

# from prompts.explainability_prompt import build_system_prompt, build_prompt
# from core.config import settings
# from services.explainability.provider import ExplanationProvider
# from services.scoring_service import ScoreComputationResult


# _FORBIDDEN_FIELD_NAMES = {
#     "name",
#     "full_name",
#     "farmer_name",
#     "national_id",
#     "phone",
#     "phone_number",
#     "participant_name",
#     "participant_phone",
# }
# _PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
# _UUID_PATTERN = re.compile(
#     r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
#     r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
#     re.IGNORECASE,
# )
# _PII_VALUE_PATTERN = re.compile(
#     r"\b(?:national\s+id|phone(?:\s+number)?|farmer\s+id|participant\s+id)"
#     r"\s*[:=]\s*[^\s,.;]{4,}",
#     re.IGNORECASE,
# )
# _FORBIDDEN_FIELD_PATTERN = re.compile(
#     r"(?<![a-z0-9_])(?:" + "|".join(map(re.escape, _FORBIDDEN_FIELD_NAMES)) + r")(?![a-z0-9_])",
#     re.IGNORECASE,
# )


# class GeminiExplanationProvider(ExplanationProvider):
#     """Generate explanations only from an allowlisted score breakdown."""

#     def __init__(
#     self, api_key: str | None = None, model_name: str | None = None
#         ) -> None:
#             configured_api_key = api_key or settings.GEMINI_API_KEY
#             if not configured_api_key:
#                 raise RuntimeError(
#                     "GEMINI_API_KEY is empty; configure it before using "
#                     "GeminiExplanationProvider"
#                 )
#             self.model_name = model_name or settings.GEMINI_MODEL
#             self.client = genai.Client(api_key=configured_api_key)

#     async def generate(
#         self, 
#         breakdown: ScoreComputationResult,
#         mode: Literal["expert", "farmer"],
#         language: str
#     ) -> str:
#         # Serialize only score fields and component-level facts. In particular,
#         # never serialize the ORM profile wholesale because it contains farmer_id.
#         payload = self._privacy_reduced_payload(breakdown)
#         system_prompt = build_system_prompt(mode)
#         prompt = build_prompt(payload, language)
#         response = await self._generate_content(system_prompt, prompt)
#         text = self._extract_text(response)
#         self._assert_safe_output(text, payload)
#         return text

#     async def _generate_content(self, system_prompt: str, prompt: str) -> Any:
#         return await self.client.aio.models.generate_content(
#         model=self.model_name,
#         contents=prompt,
#         config=types.GenerateContentConfig(
#             system_instruction=system_prompt,
#         ),
#         )
#     @staticmethod
#     def _privacy_reduced_payload(breakdown: ScoreComputationResult) -> dict[str, Any]:
#         profile = breakdown.profile
#         components = []
#         for component in breakdown.components:
#             raw_value = component.raw_value
#             if _contains_sensitive_field(raw_value):
#                 raise ValueError("Score component contains a forbidden identity field")
#             components.append(
#                 {
#                     "axis": component.axis,
#                     "component": component.component_name,
#                     "raw_value": raw_value,
#                     "contribution": component.contribution,
#                     "weight": component.weight,
#                     "pooled": component.pool_id is not None,
#                 }
#             )
#         return {
#             "final_score": profile.final_score,
#             "character_score": profile.character_score,
#             "capacity_score": profile.capacity_score,
#             "decision": profile.decision,
#             "recommended_amount": profile.recommended_amount,
#             "axis_note": breakdown.axis_note,
#             "components": components,
#         }

#     @staticmethod
#     def _extract_text(response: Any) -> str:
#         text = getattr(response, "text", None)
#         if not isinstance(text, str) or not text.strip():
#             raise ValueError("Gemini returned no explanation text")
#         return text.strip()

#     @staticmethod
#     def _assert_safe_output(text: str, payload: dict[str, Any]) -> None:
#         # Generic words such as "name" are safe in a privacy explanation. The
#         # output guard instead rejects PII-shaped values and explicit key/value
#         # disclosures, while the input guard remains strict about field names.
#         if _contains_sensitive_output(text):
#             raise ValueError("Gemini explanation contains a forbidden identity field")


# def _contains_sensitive_field(value: Any) -> bool:
#     if not isinstance(value, str):
#         return False
#     return bool(_FORBIDDEN_FIELD_PATTERN.search(value) or _PHONE_PATTERN.search(value))


# def _contains_sensitive_output(value: Any) -> bool:
#     if not isinstance(value, str):
#         return False
#     return bool(
#         _PHONE_PATTERN.search(value)
#         or _UUID_PATTERN.search(value)
#         or _PII_VALUE_PATTERN.search(value)
#     )

"""Groq explanation provider with an explicit PII boundary."""

from __future__ import annotations

import re
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from core.config import settings
from prompts.explainability_prompt import build_prompt, build_system_prompt
from services.explainability.provider import ExplanationProvider
from services.scoring_service import ScoreComputationResult

_FORBIDDEN_FIELD_NAMES = {
    "name",
    "full_name",
    "farmer_name",
    "national_id",
    "phone",
    "phone_number",
    "participant_name",
    "participant_phone",
}
_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
_UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_PII_VALUE_PATTERN = re.compile(
    r"\b(?:national\s+id|phone(?:\s+number)?|farmer\s+id|participant\s+id)"
    r"\s*[:=]\s*[^\s,.;]{4,}",
    re.IGNORECASE,
)
_FORBIDDEN_FIELD_PATTERN = re.compile(
    r"(?<![a-z0-9_])(?:" + "|".join(map(re.escape, _FORBIDDEN_FIELD_NAMES)) + r")(?![a-z0-9_])",
    re.IGNORECASE,
)


class GroqExplanationProvider(ExplanationProvider):
    """Generate explanations only from an allowlisted score breakdown using Groq."""

    def __init__(
        self, api_key: str | None = None, model_name: str | None = None
    ) -> None:
        configured_api_key = api_key or getattr(settings, "GROQ_API_KEY", None)
        if not configured_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is empty; configure it before using "
                "GroqExplanationProvider"
            )
        self.model_name = model_name or getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")
        self.client = ChatGroq(
            model=self.model_name,
            api_key=configured_api_key,
        )

    async def generate(
        self, 
        breakdown: ScoreComputationResult,
        mode: Literal["expert", "farmer"],
        language: str
    ) -> str:
        # Serialize only score fields and component-level facts.
        payload = self._privacy_reduced_payload(breakdown)
        system_prompt = build_system_prompt(mode)
        prompt = build_prompt(payload, language)
        
        response = await self._generate_content(system_prompt, prompt)
        text = self._extract_text(response)
        self._assert_safe_output(text, payload)
        return text

    async def _generate_content(self, system_prompt: str, prompt: str) -> Any:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]
        # ChatGroq supports async invocation out of the box via ainvoke
        return await self.client.ainvoke(messages)

    @staticmethod
    def _privacy_reduced_payload(breakdown: ScoreComputationResult) -> dict[str, Any]:
        profile = breakdown.profile
        components = []
        for component in breakdown.components:
            raw_value = component.raw_value
            if _contains_sensitive_field(raw_value):
                raise ValueError("Score component contains a forbidden identity field")
            components.append(
                {
                    "axis": component.axis,
                    "component": component.component_name,
                    "raw_value": raw_value,
                    "contribution": component.contribution,
                    "weight": component.weight,
                    "pooled": component.pool_id is not None,
                }
            )
        return {
            "final_score": profile.final_score,
            "character_score": profile.character_score,
            "capacity_score": profile.capacity_score,
            "decision": profile.decision,
            "recommended_amount": profile.recommended_amount,
            "axis_note": breakdown.axis_note,
            "components": components,
        }

    @staticmethod
    def _extract_text(response: Any) -> str:
        text = getattr(response, "content", None)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Groq returned no explanation text")
        return text.strip()

    @staticmethod
    def _assert_safe_output(text: str, payload: dict[str, Any]) -> None:
        if _contains_sensitive_output(text):
            raise ValueError("Groq explanation contains a forbidden identity field")


def _contains_sensitive_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_FORBIDDEN_FIELD_PATTERN.search(value) or _PHONE_PATTERN.search(value))


def _contains_sensitive_output(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(
        _PHONE_PATTERN.search(value)
        or _UUID_PATTERN.search(value)
        or _PII_VALUE_PATTERN.search(value)
    )