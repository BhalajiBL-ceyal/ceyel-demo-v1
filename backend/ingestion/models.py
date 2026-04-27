"""
Pydantic models for the Event Ingestion API.
Validates incoming JSON payloads and shapes responses.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EventIn(BaseModel):
    """Schema for an incoming event from external systems."""
    case_id: str = Field(..., description="Unique case/process instance identifier")
    timestamp: str = Field(..., description="ISO 8601 datetime string of when the activity occurred")
    activity: str = Field(..., description="Name of the process activity performed")
    actor: Optional[str] = Field(default="", description="User or system that performed the activity")
    cost: Optional[float] = Field(default=0.0, description="Cost associated with this activity (monetary units)")
    duration: Optional[float] = Field(default=0.0, description="Duration of this activity in minutes")


class EventOut(BaseModel):
    """Schema for an event returned by the API (includes DB id and hash)."""
    id: int
    case_id: str
    timestamp: str
    activity: str
    actor: str
    cost: float
    duration: float
    event_hash: str

    class Config:
        from_attributes = True


class BulkIngestionResult(BaseModel):
    """Summary of a bulk event ingestion operation."""
    ingested: int
    failed: int
    message: str
