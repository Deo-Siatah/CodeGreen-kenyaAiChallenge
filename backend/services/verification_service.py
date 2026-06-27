from typing import Optional, Dict, List
from datetime import datetime
import uuid
import logging

from repositories.verification_session_repository import VerificationSessionRepository
from repositories.participant_response_repository import ParticipantResponseRepository
from repositories.verification_log_repository import VerificationLogRepository
from repositories.farmer_repository import FarmerRepository
from services.scoring_service import ScoringService
from services.sms_service import SmsService
from services.question_service import QuestionEngine
from utils.phone_normalization import normalize_phone
logger = logging.getLogger(__name__)


class VerificationService:
    def __init__(
        self,
        session_repo: VerificationSessionRepository,
        response_repo: ParticipantResponseRepository,
        log_repo: VerificationLogRepository,
        farmer_repo: FarmerRepository,
        scoring_service: ScoringService,
        sms_service: SmsService,
        question_service: QuestionEngine
    ):
        self.session_repo = session_repo
        self.response_repo = response_repo
        self.log_repo = log_repo
        self.farmer_repo = farmer_repo
        self.scoring_service = scoring_service
        self.sms_service = sms_service
        self.question_service = question_service
    
    # ============ START VERIFICATION ============
    
    def start_verification(self, farmer_id: str) -> Dict:
        """
        1. Create VerificationSession
        2. Load farmer's trust sources
        3. Create ParticipantResponse records (pending)
        4. Log the event
        5. Return session info
        """
        
        logger.info(f"Starting verification for farmer_id={farmer_id}")
        
        # Get farmer
        farmer = self.farmer_repo.get_by_id(farmer_id)
        if not farmer:
            raise ValueError(f"Farmer {farmer_id} not found")
        
        logger.info(f"Farmer found: {farmer}")
        
        farmer_name = farmer.get('full_name', 'Unknown')
        logger.info(f"Farmer name: {farmer_name}, Type: {type(farmer_name)}")
        
        # Ensure farmer_name is a string
        if farmer_name is None:
            farmer_name = 'Unknown'
        farmer_name = str(farmer_name).strip()
        
        # Create session using VerificationSessionRepository
        try:
            session = self.session_repo.create_session(
                farmer_id=str(farmer_id).strip(),
                farmer_name=farmer_name
            )
            logger.info(f"Session created: {session}")
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}", exc_info=True)
            raise
    
    # ... rest of the code
        
        session_id = session["id"]
        
        # Log: Verification started
        self.log_repo.create_log_entry(
            session_id=session_id,
            event="VERIFICATION_STARTED",
            details={"farmer_id": farmer_id, "farmer_name": farmer_name}
        )
        
        # Get farmer trust sources
        trust_sources = self.farmer_repo.get_trust_sources(farmer_id)
        
        participants = []
        
        for idx, trust_source in enumerate(trust_sources, 1):
            participant_type = trust_source.get("category")  # Chief, Agrovet, Buyer
            participant_name = trust_source.get("name")
            participant_phone = normalize_phone(trust_source.get("phone"))
            if not participant_phone:
                logger.warning(
                    f"Skipping {participant_name}: missing phone."
                )
                continue
            
            # Get questions for this participant type
            
            
            # Create ParticipantResponse record
            self.response_repo.create_participant_response(
                session_id=session_id,
                participant_type=participant_type,
                participant_name=participant_name,
                participant_phone=participant_phone
            )
            
            # Log: Participant contacted
            self.log_repo.create_log_entry(
                session_id=session_id,
                event="PARTICIPANT_CONTACTED",
                details={
                    "participant_type": participant_type,
                    "participant_name": participant_name,
                    "participant_phone": participant_phone
                },
                participant_type=participant_type,
                participant_phone=participant_phone
            )
            
            
            participants.append({
                "type": participant_type,
                "name": participant_name,
                "phone": participant_phone,
                "status": "pending"
            })
        
        return {
            "session_id": session_id,
            "farmer_id": farmer_id,
            "farmer_name": farmer_name,
            "status": "pending",
            "participants_awaiting": participants,
            "message": f"Verification started. {len(participants)} participants contacted.",
            "created_at": session.get("created_at")
        }
    
    # ============ PROCESS RESPONSE ============
    
    def process_ussd_response(
        self,
        session_id: str,
        participant_phone: str,
        question_id: str,
        answer: str
    ) -> Dict:
        """
        1. Validate response
        2. Add response to ParticipantResponse
        3. Check if all questions answered
        4. If complete, mark as received and calculate score
        5. Return status
        """
        
        participant_phone = normalize_phone(participant_phone)
        
        # Get participant response record
        response = self.response_repo.get_by_session_and_phone(
            session_id, participant_phone
        )
        
        if not response:
            raise ValueError(f"No pending response for {participant_phone} in session {session_id}")
        
        # Add response
        updated_response = self.response_repo.add_response(
            session_id=session_id,
            participant_phone=participant_phone,
            question_id=question_id,
            answer=answer
        )
        
        # Log response
        self.log_repo.create_log_entry(
            session_id=session_id,
            event="RESPONSE_RECEIVED",
            details={
                "question_id": question_id,
                "answer": answer
            },
            participant_type=response.get("participant_type"),
            participant_phone=participant_phone
        )
        
        # Check if all questions answered
        questions = self.question_service.get_questions(response.get("participant_type"))
        all_answered = len(updated_response.get("responses", [])) >= len(questions)
        
        if all_answered:
            # Mark as received
            self.response_repo.mark_as_received(session_id, participant_phone)
            
            self.log_repo.create_log_entry(
                session_id=session_id,
                event="PARTICIPANT_COMPLETE",
                details={
                    "participant_type": response.get("participant_type"),
                    "total_responses": len(updated_response.get("responses", []))
                },
                participant_type=response.get("participant_type"),
                participant_phone=participant_phone
            )
        
        # Get current status
        status = self.response_repo.get_session_status(session_id)
        
                
        # Check if all responses received
        all_complete = len(status["pending"]) == 0 and len(status["timeout"]) == 0
        
        session_status = "complete" if all_complete else "pending"
        
        if all_complete:
            final_result = self.scoring_service.calculate_final_score(status)

            self.session_repo.update_status(
                session_id,
                "complete"
            )

            self.log_repo.create_log_entry(
                session_id=session_id,
                event="VERIFICATION_COMPLETE",
                details={
                    "trust_score": final_result["trust_score"],
                    "decision": final_result["decision"]
                }
    )
        else:
            # Log current score update
            self.log_repo.create_log_entry(
                session_id=session_id,
                event="CURRENT_SCORE_UPDATED",
                details={
                    "received": len(status["received"]),
                    "pending": len(status["pending"])
                }
            )
        
        return {
            "session_id": session_id,
            "status": session_status,
            "received": len(status["received"]),
            "pending": len(status["pending"]),
            "timeout": len(status["timeout"]),
            "message": f"{len(status['received'])} responses received. Awaiting {len(status['pending'])}.",
            "participants_status": status
        }
    
    # ============ SIMULATE TIMEOUT ============
    
    def simulate_timeout(
        self,
        session_id: str,
        participant_phone: str
    ) -> Dict:
        """Mark participant as timeout (for demo)"""
        
        participant_phone = normalize_phone(participant_phone)
        
        response = self.response_repo.get_by_session_and_phone(
            session_id, participant_phone
        )
        
        if not response:
            raise ValueError(f"No response for {participant_phone} in session {session_id}")
        
        # Mark as timeout
        self.response_repo.mark_as_timeout(session_id, participant_phone)
        
        self.log_repo.create_log_entry(
            session_id=session_id,
            event="PARTICIPANT_TIMEOUT",
            details={
                "participant_type": response.get("participant_type"),
                "reason": "48h timeout reached"
            },
            participant_type=response.get("participant_type"),
            participant_phone=participant_phone
        )
        
        # Get current status
        status = self.response_repo.get_session_status(session_id)
        
        # Calculate current score (with timeout included)
        current_score = self.scoring_service.calculate_current_score(status)
        
        # Check if verification should be considered complete now
        all_final = len(status["pending"]) == 0
        
        if all_final:
            self.session_repo.update_status(session_id, "timeout")
            final_result = self.scoring_service.calculate_final_score(status)
            self.log_repo.create_log_entry(
                session_id=session_id,
                event="VERIFICATION_TIMEOUT_COMPLETE",
                details={
                    "trust_score": final_result["trust_score"],
                    "decision": final_result["decision"],
                    "received": len(status["received"]),
                    "timeout": len(status["timeout"])
                }
            )
        
        return {
            "session_id": session_id,
            "status": "timeout" if all_final else "pending",
            "received": len(status["received"]),
            "timeout": len(status["timeout"]),
            "pending": len(status["pending"]),
            "current_score": current_score,
            "message": f"Participant marked as timeout. Current score: {current_score}"
        }
    
    # ============ GET STATUS ============
    
    def get_status(self, session_id: str) -> Dict:
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        status = self.response_repo.get_session_status(session_id)
        current_score = self.scoring_service.calculate_current_score(status)

        # Flatten participants into a list
        participants = status["received"] + status["pending"] + status["timeout"]

        return {
            "session_id": session_id,
            "status": session.get("status"),
            "participants": participants,   # ✅ now a list
            "received": len(status["received"]),
            "pending": len(status["pending"]),
            "timeout": len(status["timeout"]),
            "current_score": current_score,
            "message": f"{len(status['received'])} responses received. Awaiting {len(status['pending'])}."
        }


    
    # ============ GET FINAL RESULT ============
    
    def get_final_result(self, session_id: str) -> Dict:
        """Get final verification result (only when complete)"""
        
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.get("status") not in ["complete", "timeout"]:
            raise ValueError(f"Session {session_id} is still {session.get('status')}, not complete")
        
        status = self.response_repo.get_session_status(session_id)
        
        # Calculate final score
        final_result = self.scoring_service.calculate_final_score(status)
        
        return {
            "session_id": session_id,
            "farmer_id": session.get("farmer_id"),
            "farmer_name": session.get("farmer_name"),
            "status": session.get("status"),
            "created_at": session.get("created_at"),
            "completed_at": session.get("completed_at"),
            "trust_score": final_result["trust_score"],
            "decision": final_result["decision"],
            "recommendation": final_result["recommendation"],
            "loan_amount_recommended_kes": final_result.get("loan_amount_recommended_kes"),
            "participant_scores": final_result["participant_scores"],
            "analysis": final_result["analysis"]
        }
    
    # ============ SEND FINAL SMS ============
    
    def send_final_sms(
        self,
        session_id: str,
        farmer_phone: str
    ) -> Dict:
        """Send final SMS to farmer"""
        
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.get("status") not in ["complete", "timeout"]:
            raise ValueError(f"Session {session_id} is still {session.get('status')}, not complete")
        
        # Get final result
        final_result = self.get_final_result(session_id)
        
        # Format SMS (basic - Phase 3 will translate to Kiswahili)
        sms_message = self._format_sms_message(final_result)
        
        # Send SMS
        sms_response = self.sms_service.send_sms(
            phone=normalize_phone(farmer_phone),
            message=sms_message,
            session_id=session_id
        )
        
        # Log SMS sent
        self.log_repo.create_log_entry(
            session_id=session_id,
            event="FINAL_SMS_SENT",
            details={
                "farmer_phone": farmer_phone,
                "sms_id": sms_response.get("sms_id"),
                "decision": final_result.get("decision")
            }
        )
        
        return {
            "session_id": session_id,
            "status": "sms_sent",
            "farmer_phone": farmer_phone,
            "message_sent": sms_message,
            "sms_id": sms_response.get("sms_id"),
            "sent_at": datetime.now().isoformat(),
            "message": "SMS sent successfully. Farmer will receive shortly."
        }
    
    # ============ GET LOGS ============
    
    def get_logs(self, session_id: str) -> Dict:
        """Get all logs for a session"""
        
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        logs = self.log_repo.get_logs(session_id)
        
        return {
            "session_id": session_id,
            "created_at": session.get("created_at"),
            "farmer_id": session.get("farmer_id"),
            "farmer_name": session.get("farmer_name"),
            "events": logs
        }
    
    # ============ HELPERS ============
    
    def _format_sms_message(self, final_result: Dict) -> str:
        """Format final result as SMS message (to be translated in Phase 3)"""
        
        decision = final_result.get("decision")
        recommendation = final_result.get("recommendation")
        score = final_result.get("trust_score")
        amount = final_result.get("loan_amount_recommended_kes", 0)
        
        if decision == "ELIGIBLE":
            drivers = " • ".join(final_result["analysis"]["key_drivers"][:3])
            return (
                f"APPROVED: {recommendation}\n"
                f"Amount: KES {amount:,.0f}\n"
                f"Score: {score:.0f}/100\n\n"
                f"Reasons:\n• {drivers}\n\n"
                f"Visit agrovet to collect voucher."
            )
        elif decision == "REVIEW_REQUIRED":
            return (
                f"Under Review\n"
                f"Score: {score:.0f}/100\n\n"
                f"Your application is under review.\n"
                f"Contact your loan officer for details."
            )
        else:
            return (
                f"Not Approved\n"
                f"Score: {score:.0f}/100\n\n"
                f"Your application was not approved.\n"
                f"Contact your loan officer for details."
            )