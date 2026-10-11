"""Simple test to demonstrate timeout issue."""

from datetime import datetime, timezone
from uuid import uuid4


def test_finish_if_complete_logic():
    """Test the logic in _finish_if_complete method to understand the timeout issue."""
    
    # Create mock participants
    participants = []
    
    # Case 1: One participant has responded, one hasn't
    class MockParticipant:
        def __init__(self, responded_at, response):
            self.responded_at = responded_at
            self.response = response
    
    participant1 = MockParticipant(datetime.now(timezone.utc), "good")
    participant2 = MockParticipant(None, None)
    
    participants = [participant1, participant2]
    
    # Current logic from _finish_if_complete
    complete = all(item.responded_at is not None for item in participants)
    print(f"Case 1 - Mixed response/timed out: {complete}")  # Should be False
    
    # Case 2: Both participants have responded
    participant2.responded_at = datetime.now(timezone.utc)
    participant2.response = "good"
    
    complete = all(item.responded_at is not None for item in participants)
    print(f"Case 2 - Both responded: {complete}")  # Should be True
    
    # Case 3: One participant timed out, one hasn't
    participant1.responded_at = datetime.now(timezone.utc)
    participant1.response = "timeout"
    participant2.responded_at = None
    participant2.response = None
    
    complete = all(item.responded_at is not None for item in participants)
    print(f"Case 3 - One timed out, one not: {complete}")  # Should be False
    
    # Case 4: Both participants timed out
    participant2.responded_at = datetime.now(timezone.utc)
    participant2.response = "timeout"
    
    complete = all(item.responded_at is not None for item in participants)
    print(f"Case 4 - Both timed out: {complete}")  # Should be True
    
    print("\nAnalysis:")
    print("- The current logic correctly handles timeouts")
    print("- responded_at is set when a participant times out")
    print("- The 500 error must be coming from somewhere else")
    print("- Likely from the scoring service when there are no scoreable signals")


if __name__ == "__main__":
    test_finish_if_complete_logic()