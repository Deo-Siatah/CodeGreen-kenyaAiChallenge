class WeightingService:
    
    WEIGHTS = {
        "Chief": 4,
        "Assistant Chief": 3,
        "Village Elder": 3,
        "Religious Leader": 3,
        "Teacher": 3,
        "School Head": 4,
        "Health Worker": 3,
        "Agrovet Owner": 3,
        "Cooperative Officer": 4,
        "SACCO Officer": 4,
        "Neighbor": 1,
        "Buyer": 4,
        "Trader": 3,
        "Retailer": 3,
        "Aggregator": 4,
        "Chama": 3,
        "Savings Group": 4,
        "Youth Group": 3,
        "Women's Group": 3
    }
    
    def get_weight(self, participant_type: str) -> float:
        """Get weight for participant type"""
        
        return self.WEIGHTS.get(participant_type, 1)