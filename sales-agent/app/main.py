import sys
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import leads, strategy, settings, outreach
from app.database.database import engine, Base
import logging

logging.basicConfig(level=logging.INFO)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Intelligent Multi-Agent AI Sales Automation System",
    description="Integration 1 - Lead Generation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router)
app.include_router(strategy.router)
app.include_router(settings.router)
app.include_router(outreach.router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
