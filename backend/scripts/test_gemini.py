# import json

from services.gemini_service import GeminiService

# payload = {

#     "trust_score": 86.11,

#     "decision": "ELIGIBLE",

#     "recommendation": "APPROVE_LEVEL_2",

#     "loan_amount": 5000,

#     "analysis": {

#         "summary":
#             "Strong community verification.",

#         "explanation":
#             "The farmer achieved a trust score of 86/100.",

#         "key_drivers": [

#             "Chief verification was positive.",

#             "Agrovet verification was positive.",

#             "Buyer verification was positive."

#         ],

#         "risk_factors": [

#             "No major verification risks."

#         ]

#     },

#     "participant_summary":[

#         {

#             "participant_type":"CHIEF",

#             "raw_score":75,

#             "weighted_score":75,

#             "response_count":4

#         },

#         {

#             "participant_type":"AGROVET",

#             "raw_score":83,

#             "weighted_score":83,

#             "response_count":3

#         },

#         {

#             "participant_type":"BUYER",

#             "raw_score":100,

#             "weighted_score":100,

#             "response_count":3

#         }

#     ]

# }

# service = GeminiService()

# response = service.generate(payload)

# print()

# print("=" * 80)

# print(json.dumps(response, indent=4))

# print("=" * 80)

import requests

verification = requests.get(
    "http://localhost:8000/api/verify/00576492-2dcc-47c3-9447-d882c9695ec9/result"
).json()

response = GeminiService().generate_explanation(
    verification
)

print(response)