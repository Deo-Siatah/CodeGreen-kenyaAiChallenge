from typing import Dict
from utils.phone_normalization import normalize_phone


class USSDService:
    def __init__(self, question_service, verification_service):
        self.question_service = question_service
        self.verification_service = verification_service

    # ==========================================================
    # START USSD SESSION
    # ==========================================================

    def start_ussd(
        self,
        phone: str,
        session_id: str,      # Africa's Talking session id (not used for lookup)
        ussd_code: str
    ) -> Dict:
        """
        Start a USSD session.

        Africa's Talking provides:
            - phone
            - AT session id
            - service code

        We identify the participant using their phone number because
        the VerificationSession UUID already exists in our database.
        """

        phone = normalize_phone(phone)

        # Find pending verification assigned to this phone
        participant = (
            self.verification_service.response_repo
            .get_active_by_phone(phone)
        )

        if not participant:
            return {
                "ussd_text": "No active verification assigned to this phone.",
                "session_state": "error"
            }
        
        print("🔴Participant Record:")
        print(participant)
        participant_type = participant["participant_type"]

        questions = self.question_service.get_questions(
            participant_type
        )

        if not questions:
            return {
                "ussd_text": "No questions configured.",
                "session_state": "error"
            }

        current_question = questions[0]

        ussd_text = (
            f"Verification\n\n"
            f"Q1/{len(questions)}\n"
            f"{current_question['text']}\n\n"
            f"1. YES\n"
            f"2. NO\n"
            f"3. UNSURE"
        )

        return {
            "ussd_text": ussd_text,
            "session_state": "question",
            "question_number": 1,
            "total_questions": len(questions)
        }

    # ==========================================================
    # PROCESS RESPONSE
    # ==========================================================

    def process_ussd_response(
        self,
        phone: str,
        session_id: str,      # Africa's Talking session id (ignored)
        user_input: str
    ) -> Dict:

        phone = normalize_phone(phone)

        # ------------------------------------------------------
        # Find participant using phone
        # ------------------------------------------------------

        participant = (
            self.verification_service.response_repo
            .get_active_by_phone(phone)
        )

        if not participant:
            return {
                "ussd_text": "Session expired.",
                "session_state": "error"
            }

        verification_session_id = participant["session_id"]

        participant_type = participant["participant_type"]

        questions = self.question_service.get_questions(
            participant_type
        )

        responses = participant.get("responses", [])

        current_question_idx = len(responses)

        # ------------------------------------------------------
        # Validate input
        # ------------------------------------------------------

        input_map = {
            "1": "YES",
            "2": "NO",
            "3": "UNSURE"
        }

        answer = input_map.get(user_input.strip())

        if answer is None:
            return {
                "ussd_text": "Invalid input.\n1.YES\n2.NO\n3.UNSURE",
                "session_state": "question"
            }

        # ------------------------------------------------------
        # Save current answer
        # ------------------------------------------------------

        current_question = questions[current_question_idx]

        self.verification_service.process_ussd_response(
            session_id=verification_session_id,
            participant_phone=phone,
            question_id=current_question["id"],
            answer=answer
        )

        # ------------------------------------------------------
        # Move to next question
        # ------------------------------------------------------

        current_question_idx += 1

        if current_question_idx < len(questions):

            next_question = questions[current_question_idx]

            ussd_text = (
                f"Q{current_question_idx + 1}/{len(questions)}\n"
                f"{next_question['text']}\n\n"
                f"1. YES\n"
                f"2. NO\n"
                f"3. UNSURE"
            )

            return {
                "ussd_text": ussd_text,
                "session_state": "question",
                "question_number": current_question_idx + 1,
                "total_questions": len(questions)
            }

        # ------------------------------------------------------
        # Finished
        # ------------------------------------------------------

        return {
            "ussd_text": (
                "Thank you.\n"
                "Your responses have been recorded."
            ),
            "session_state": "complete",
            "message": "Verification completed"
        }