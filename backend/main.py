"""Truth Oracle — FastAPI 入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.investigation_routes import router as investigation_router

app = FastAPI(title="Truth Oracle API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(investigation_router)


@app.get("/")
def root():
    return {"project": "Truth Oracle", "hackathon": "ETH Beijing 2026"}
