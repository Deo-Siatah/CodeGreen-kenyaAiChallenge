import json
import os

import google.generativeai as genai

from prompts.explainability_prompt import (
    SYSTEM_PROMPT,
    build_prompt
)

class GeminiService:

    def __init__(self):

        genai.configure(
            api_key=os.getenv("GEMINI_API_KEY")
        )

        self.model = genai.GenerativeModel(
            "gemini-2.5-flash"
        )

    def generate_explanation(
        self,
        payload: dict
    ) -> dict:

        prompt = build_prompt(payload)

        response = self.model.generate_content(

            [
                SYSTEM_PROMPT,
                prompt
            ]

        )

        text = response.text.strip()

        if text.startswith("```json"):
            text = text.replace(
                "```json",
                ""
            )

            text = text.replace(
                "```",
                ""
            )

        return json.loads(text)