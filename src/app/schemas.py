"""Pydantic request and response schemas for the chat API."""

from pydantic import BaseModel, Field
from typing import List, Optional


class ChatRequest(BaseModel):
    """Incoming chat request payload."""

    query: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Outgoing chat response payload."""

    reply: str
    intent: Optional[str] = None
    retrieved_movies: List[str] = Field(default_factory=list)
