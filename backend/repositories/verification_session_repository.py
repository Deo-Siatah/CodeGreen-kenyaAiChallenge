from repositories.base_repository import BaseRepository
from datetime import datetime
from typing import Optional, Dict
import uuid
import logging

logger = logging.getLogger(__name__)


class VerificationSessionRepository(BaseRepository):

    def create_session(self, farmer_id: str, farmer_name: str) -> Dict:
        """Create a new VerificationSession"""
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Log what we're about to do
        logger.info(f"Creating session: session_id={session_id}, farmer_id={farmer_id}, farmer_name={farmer_name}")
        logger.info(f"Types: session_id={type(session_id).__name__}, farmer_id={type(farmer_id).__name__}, farmer_name={type(farmer_name).__name__}")
        
        # Use a simpler query without date functions initially
        query = """
        MATCH (farmer:Farmer {id: $farmer_id})
        CREATE (session:VerificationSession {
            id: $session_id,
            farmer_id: $farmer_id,
            farmer_name: $farmer_name,
            status: 'pending',
            created_at: $created_at,
            completed_at: null,
            final_score: null,
            decision: null
        })
        CREATE (farmer)-[:HAS_VERIFICATION_SESSION]->(session)
        RETURN session
        """

        try:
            # Get current timestamp
            created_at = datetime.now().isoformat()
            
            with self.driver.session() as db_session:
                # Log the parameters being sent
                logger.info(f"Query parameters: {{'session_id': '{session_id}', 'farmer_id': '{farmer_id}', 'farmer_name': '{farmer_name}', 'created_at': '{created_at}'}}")
                
                # Run query with explicit parameters
                result = db_session.run(
                    query,
                    {
                        "session_id": session_id,
                        "farmer_id": farmer_id,
                        "farmer_name": farmer_name,
                        "created_at": created_at
                    }
                )
                
                record = result.single()
                
                if record:
                    session_dict = dict(record["session"])
                    logger.info(f"Session created successfully: {session_dict}")
                    return session_dict
                else:
                    error_msg = f"Farmer {farmer_id} not found in database"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}", exc_info=True)
            raise

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a VerificationSession"""
        
        query = """
        MATCH (session:VerificationSession {id: $session_id})
        RETURN session
        """
        
        try:
            with self.driver.session() as db_session:
                result = db_session.run(query, {"session_id": session_id})
                record = result.single()
                
                if record:
                    return dict(record["session"])
                return None
                
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}", exc_info=True)
            raise

    def update_status(
        self,
        session_id: str,
        status: str,
        final_score: Optional[float] = None,
        decision: Optional[str] = None
    ) -> Dict:
        """Update session status"""
        
        query = """
        MATCH (session:VerificationSession {id: $session_id})
        SET session.status = $status,
            session.completed_at = CASE 
                WHEN $status IN ['complete', 'timeout'] THEN $now
                ELSE session.completed_at
            END,
            session.final_score = COALESCE($final_score, session.final_score),
            session.decision = COALESCE($decision, session.decision)
        RETURN session
        """
        
        try:
            completed_at = datetime.now().isoformat() if status in ['complete', 'timeout'] else None
            
            with self.driver.session() as db_session:
                result = db_session.run(
                    query,
                    {
                        "session_id": session_id,
                        "status": status,
                        "final_score": final_score,
                        "decision": decision,
                        "now": completed_at
                    }
                )
                
                record = result.single()
                if record:
                    return dict(record["session"])
                return {}
                
        except Exception as e:
            logger.error(f"Error updating session status: {str(e)}", exc_info=True)
            raise