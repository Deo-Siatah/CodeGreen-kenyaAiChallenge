from services.trust_scoring_service import (
    TrustScoringService
)

from services.aggregation_service import (
    AggregationService
)

trust = TrustScoringService()

chief = trust.calculate_participant_score(
    "Chief",
    ["YES", "YES", "NO"]
)

agrovet = trust.calculate_participant_score(
    "Agrovet Owner",
    ["YES", "YES", "YES"]
)

buyer = trust.calculate_participant_score(
    "Buyer",
    ["YES", "NO"]
)

aggregation = AggregationService()

result = aggregation.aggregate([
    chief,
    agrovet,
    buyer
])

print(result)