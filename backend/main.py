from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
import models
from routers import assets, compliance, reports

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="IT Asset Compliance API",
    description="Tracks IT assets, runs security policy checks, and generates compliance reports.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets.router)
app.include_router(compliance.router)
app.include_router(reports.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy", "service": "IT Asset Compliance API", "version": "2.0.0"}
