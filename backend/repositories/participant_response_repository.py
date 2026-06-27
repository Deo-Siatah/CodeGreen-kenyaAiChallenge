from repositories.base_repository import BaseRepository
from typing import Optional, List, Dict
import uuid


class ParticipantResponseRepository(BaseRepository):

    # ============ CREATE ============
    def create_participant_response(
        self,
        session_id: str,
        participant_type: str,
        participant_name: str,
        participant_phone: str,
    ) -> Dict:
        """Create a pending ParticipantResponse node"""
        
        response_id = str(uuid.uuid4())
        
        query = """
        MATCH (session:VerificationSession {id: $session_id})
        CREATE (response:ParticipantResponse {
            id: $response_id,
            session_id: $session_id,
            participant_type: $participant_type,
            participant_name: $participant_name,
            participant_phone: $participant_phone,
            status: 'pending',
            created_at: datetime(),
            received_at: null,
            responses: []
        })
        CREATE (session)-[:HAS_RESPONSE]->(response)
        RETURN response
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                session_id=session_id,
                response_id=response_id,
                participant_type=participant_type,
                participant_name=participant_name,
                participant_phone=participant_phone
            )
            record = result.single()
            return dict(record["response"]) if record else {}

    # ============ UPDATE ============


    def mark_as_received(self, session_id: str, participant_phone: str) -> Dict:
        """Mark ParticipantResponse as complete/received"""
        
        query = """
        MATCH (response:ParticipantResponse {
            session_id: $session_id,
            participant_phone: $participant_phone
        })
        SET response.status = 'received',
            response.received_at = datetime()
        RETURN response
        """
        
        with self.driver.session() as session:
            result = session.run(query, session_id=session_id, participant_phone=participant_phone)
            record = result.single()
            return dict(record["response"]) if record else {}

    def mark_as_timeout(self, session_id: str, participant_phone: str) -> Dict:
        """Mark ParticipantResponse as timeout"""
        
        query = """
        MATCH (response:ParticipantResponse {
            session_id: $session_id,
            participant_phone: $participant_phone
        })
        SET response.status = 'timeout',
            response.received_at = datetime()
        RETURN response
        """
        
        with self.driver.session() as session:
            result = session.run(query, session_id=session_id, participant_phone=participant_phone)
            record = result.single()
            return dict(record["response"]) if record else {}

    # ============ RETRIEVE ============
    def get_by_session_and_phone(self, session_id: str, participant_phone: str) -> Optional[Dict]:
        """Get a ParticipantResponse by session and phone"""
        
        query = """
        MATCH (response:ParticipantResponse {
            session_id: $session_id,
            participant_phone: $participant_phone
        })
        RETURN response
        """
        
        with self.driver.session() as session:
            result = session.run(query, session_id=session_id, participant_phone=participant_phone)
            record = result.single()
            return dict(record["response"]) if record else None

    def get_all_by_session(self, session_id: str) -> List[Dict]:
        """Get all ParticipantResponses for a session"""
        
        query = """
        MATCH (response:ParticipantResponse {session_id: $session_id})
        RETURN response
        ORDER BY response.created_at ASC
        """
        
        with self.driver.session() as session:
            result = session.run(query, session_id=session_id)
            return [dict(record["response"]) for record in result]

    def get_session_status(self, session_id: str) -> Dict:
        """Get status of all responses for a session"""
        
        query = """
        MATCH (response:ParticipantResponse {session_id: $session_id})
        RETURN response.status as status,
               response.participant_type as type,
               response.participant_name as name,
               response.participant_phone as phone,
               response.received_at as received_at,
               response.responses as responses
        """
        
        with self.driver.session() as session:
            result = session.run(query, session_id=session_id)
            
            received, pending, timeout = [], [], []
            
            for record in result:
                response_data = {
                    "participant_type": record["type"],
                    "participant_name": record["name"],
                    "participant_phone": record["phone"],
                    "status": record["status"],
                    "received_at": record["received_at"],
                    "responses": record["responses"]
                }
                if record["status"] == "received":
                    received.append(response_data)
                elif record["status"] == "timeout":
                    timeout.append(response_data)
                else:
                    pending.append(response_data)
            
            return {"received": received, "pending": pending, "timeout": timeout}
    

    def get_active_by_phone(
    self,
    participant_phone: str
        ) -> Optional[Dict]:
            """
            Find the active pending ParticipantResponse for a phone number.

            Africa's Talking only sends the participant's phone number.
            We use this to discover the VerificationSession.
            """

            query = """
            MATCH (response:ParticipantResponse)
            WHERE response.participant_phone = $participant_phone
            AND response.status = 'pending'
            RETURN response
            ORDER BY response.created_at DESC
            LIMIT 1
            """

            with self.driver.session() as session:
                result = session.run(
                    query,
                    participant_phone=participant_phone
                )

                record = result.single()

                return dict(record["response"]) if record else None

    def add_response(
    self,
    session_id: str,
    participant_phone: str,
    question_id: str,
    answer: str
    ) -> Dict:
        """
        Add a response to a ParticipantResponse.

        Neo4j node properties cannot store arrays of maps.
        Therefore responses are stored as strings in the format:

            CH1:YES
            CH2:NO
            CH3:UNSURE
        """

        query = """
        MATCH (response:ParticipantResponse {
            session_id: $session_id,
            participant_phone: $participant_phone
        })

        SET response.responses =
            coalesce(response.responses, []) +
            [$question_id + ":" + $answer]

        RETURN response
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                session_id=session_id,
                participant_phone=participant_phone,
                question_id=question_id,
                answer=answer
            )

            record = result.single()

            return dict(record["response"]) if record else {}

