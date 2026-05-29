from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_upload import router as upload_router
from backend.api.routes_reports import router as reports_router
from backend.core.config import settings

app = FastAPI(title="Scenario Delta Report API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(reports_router)
