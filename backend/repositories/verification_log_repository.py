from repositories.base_repository import BaseRepository
from typing import List, Dict
import uuid
import json


class VerificationLogRepository(BaseRepository):

    def create_log_entry(
        self,
        session_id: str,
        event: str,
        details: Dict,
        participant_type: str = None,
        participant_phone: str = None
    ) -> Dict:
        """Create a verification log entry"""
        
        log_id = str(uuid.uuid4())
        
        query = """
        MATCH (session:VerificationSession {id: $session_id})
        CREATE (log:VerificationLog {
            id: $log_id,
            session_id: $session_id,
            event: $event,
            details: $details,
            participant_type: $participant_type,
            participant_phone: $participant_phone,
            created_at: datetime()
        })
        CREATE (session)-[:HAS_LOG]->(log)
        RETURN log
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                log_id=log_id,
                session_id=session_id,
                event=event,
                details=json.dumps(details),
                participant_type=participant_type,
                participant_phone=participant_phone
            )
            record = result.single()
            return dict(record["log"]) if record else {}

    def get_logs(self, session_id: str) -> List[Dict]:
        query = """
        MATCH (session:VerificationSession {id: $session_id})-[:HAS_LOG]->(log:VerificationLog)
        RETURN log
        ORDER BY log.created_at ASC
        """

        logs = []

        with self.driver.session() as session:
            result = session.run(query, session_id=session_id)

            for record in result:
                log = dict(record["log"])

                # Rename field
                timestamp = log.pop("created_at")

                # Convert Neo4j DateTime -> Python datetime
                log["timestamp"] = timestamp.to_native()

                # Convert JSON string -> dict
                if log.get("details"):
                    log["details"] = json.loads(log["details"])

                logs.append(log)

        return logs