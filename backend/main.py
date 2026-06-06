"""Human-AI Jury — FastAPI entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.demo_routes import router as demo_router
from .api.investigation_routes import router as investigation_router

app = FastAPI(title="Human-AI Jury API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(investigation_router)
app.include_router(demo_router)


@app.get("/")
def root():
    return {
        "project": "Human-AI Jury",
        "hackathon": "ETH Beijing 2026",
        "layers": ["investigation", "deliberation", "frontend", "chain"],
    }
