from fastapi import FastAPI

from api.farmers import router as farmers_router
from api.trust import router as trust_router
from api.relationship import router as relationships_router
from api.verification import router as verification_router

app = FastAPI(
    title="AgriForesight API"
)

app.include_router(farmers_router)
app.include_router(trust_router)
app.include_router(relationships_router)
app.include_router(verification_router)