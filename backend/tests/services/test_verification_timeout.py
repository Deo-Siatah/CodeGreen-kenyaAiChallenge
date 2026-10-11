"""Service-level test for timeout scenarios."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from services.verification_service import VerificationService
from services.scoring_service import ScoringService
from models.verification import VerificationSession, VerificationParticipant
from repositories.verification_repository import VerificationRepository


class TestVerificationTimeout:
    """Test timeout scenarios in verification service."""

    @pytest.mark.asyncio
    async def test_timeout_single_non_final_participant(self):
        """Test timing out a single non-final participant - should not complete session."""
        # Create test data
        session_id = uuid4()
        farmer_id = uuid4()
        
        # Create verification session
        verification_session = VerificationSession(
            id=session_id,
            farmer_id=farmer_id,
            status="in_progress",
            created_at=datetime.now(timezone.utc),
        )
        
        # Create two participants
        participant1 = VerificationParticipant(
            id=uuid4(),
            session_id=session_id,
            participant_type="trust_source",
            participant_id=str(uuid4()),
            contacted_at=datetime.now(timezone.utc),
        )
        
        participant2 = VerificationParticipant(
            id=uuid4(),
            session_id=session_id,
            participant_type="market_actor", 
            participant_id=str(uuid4()),
            contacted_at=datetime.now(timezone.utc),
        )
        
        # Mock the verification repository
        mock_repo = VerificationRepository()
        
        # Create verification service with mocked dependencies
        service = VerificationService(verification_repository=mock_repo)
        
        # Mock database session
        class MockSession:
            async def execute(self, query):
                # Mock the query results
                if "VerificationSession" in str(query):
                    return type('MockResult', (), {'scalar_one_or_none': lambda: verification_session})()
                elif "VerificationParticipant" in str(query):
                    return type('MockResult', (), {'scalar_one_or_none': lambda: participant1})()
                return type('MockResult', (), {'scalar_one_or_none': lambda: None})()
            
            async def flush(self):
                pass
        
        mock_session = MockSession()
        
        try:
            # Timeout the first participant
            result = await service.mark_participant_timeout(mock_session, session_id, participant1.id)
            
            # Check that session is not completed
            assert result["session_status"] == "in_progress"
            assert result["score_result"] is None
            assert result["participant_status"] == "timeout"
            
            # Now timeout the second participant
            result2 = await service.mark_participant_timeout(mock_session, session_id, participant2.id)
            
            # Check that session is now completed
            assert result2["session_status"] == "completed"
            assert result2["score_result"] is not None
            
        except Exception as exc:
            print(f"Exception type: {type(exc).__name__}")
            print(f"Exception message: {str(exc)}")
            import traceback
            print("Traceback:")
            traceback.print_exc()
            raise


if __name__ == "__main__":
    import asyncio
    
    async def run_test():
        test = TestVerificationTimeout()
        await test.test_timeout_single_non_final_participant()
    
    asyncio.run(run_test())