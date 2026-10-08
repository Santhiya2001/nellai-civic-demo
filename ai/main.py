"""Versioned classifier contract. No trained image model is bundled or claimed."""

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Nellai AI provider contract", version="0.1.0")


class ClassificationRequest(BaseModel):
    description: str = Field(min_length=1, max_length=5000)
    image_sha256: str | None = Field(default=None, pattern="^[a-f0-9]{64}$")


class Prediction(BaseModel):
    provider: str
    model_version: str | None = None
    available: bool
    predicted_category: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    severity: str | None = None
    reason: str


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": False}


@app.post("/v1/classify", response_model=Prediction)
def classify(data: ClassificationRequest):
    return Prediction(
        provider="disabled",
        available=False,
        reason="No trained model configured. Human classification remains authoritative.",
    )
