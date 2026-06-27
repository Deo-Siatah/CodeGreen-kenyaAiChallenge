from fastapi import FastAPI

from api.farmers import router as farmers_router
from api.trust import router as trust_router
from api.relationship import router as relationships_router
from api.verification_sources import router as appverification_router
from api.app import router as appverification_router
from api.response import router as response_router
from api.verification import router as verification_router
from api.ussd import router as ussd_router

app = FastAPI(
    title="AgriForesight API"
)

app.include_router(farmers_router)
app.include_router(trust_router)
app.include_router(relationships_router)
app.include_router(verification_router)
app.include_router(
    appverification_router
)
app.include_router(response_router)
app.include_router(appverification_router)
app.include_router(ussd_router)