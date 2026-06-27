from typing import List, Dict


class QuestionEngine:
    
    QUESTION_BANK = {
        "Chief": [
            {
                "id": "CH1",
                "text": "Is this farmer known and respected in your area?",
                "category": "character"
            },
            {
                "id": "CH2",
                "text": "Would you recommend this farmer for credit?",
                "category": "creditworthiness"
            },
            {
                "id": "CH3",
                "text": "Do you believe this farmer is trustworthy?",
                "category": "character"
            },
            {
                "id": "CH4",
                "text": "Does this farmer honor their obligations?",
                "category": "repayment"
            }
        ],
        "Agrovet": [
            {
                "id": "AG1",
                "text": "Is this farmer a regular customer?",
                "category": "market_access"
            },
            {
                "id": "AG2",
                "text": "Does this farmer pay on time?",
                "category": "repayment"
            },
            {
                "id": "AG3",
                "text": "Is this farmer reliable in their purchases?",
                "category": "farming_activity"
            }
        ],
        "Buyer": [
            {
                "id": "BY1",
                "text": "Do you know this farmer as a supplier?",
                "category": "market_access"
            },
            {
                "id": "BY2",
                "text": "Does this farmer deliver consistently?",
                "category": "farming_activity"
            },
            {
                "id": "BY3",
                "text": "Is the quality of their produce good?",
                "category": "farming_activity"
            }
        ],
        "Chama": [
            {
                "id": "CH1",
                "text": "Is this farmer an active member?",
                "category": "savings_behavior"
            },
            {
                "id": "CH2",
                "text": "Does this farmer contribute regularly?",
                "category": "savings_behavior"
            },
            {
                "id": "CH3",
                "text": "Has this farmer honored group commitments?",
                "category": "repayment"
            }
        ]
    }
    
    def get_questions(self, participant_type: str) -> List[Dict]:
        """
        Return questions for a participant type.

        Normalizes different naming conventions
        (CHIEF, Chief, chief, etc.)
        """

        participant_type = participant_type.strip().upper()

        mapping = {
            "CHIEF": "Chief",
            "AGROVET": "Agrovet",
            "BUYER": "Buyer",
            "CHAMA": "Chama"
        }

        normalized = mapping.get(participant_type, participant_type.title())

        return list(self.QUESTION_BANK.get(normalized, []))

    def format_sms_questions(
        self,
        participant_type: str,
        session_id: str
    ) -> str:
        """Format questions as SMS menu"""
        
        questions = self.get_questions(participant_type)
        
        sms = f"Verification Session: {session_id[:8]}\n\n"
        
        for idx, question in enumerate(questions, 1):
            sms += f"Q{idx}: {question['text']}\n"
            sms += "[1]YES [2]NO [3]UNSURE\n\n"
        
        return sms