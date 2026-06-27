class GeminiParser:

    REQUIRED_FIELDS = {
        "credit_profile": {
            "category": "",
            "summary": ""
        },
        "risk_signals": [],
        "positive_signals": [],
        "negative_signals": [],
        "loan_officer_explanation": "",
        "farmer_explanation": "",
        "fairness_explanation": "",
        "kiswahili_translation": "",
        "voice_script": ""
    }

    def parse(self, response: dict):

        result = self.REQUIRED_FIELDS.copy()

        for key in result:

            if key in response:
                result[key] = response[key]

        return result