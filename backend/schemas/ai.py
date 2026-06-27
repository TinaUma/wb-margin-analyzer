from __future__ import annotations

from pydantic import BaseModel


class InterpretResponse(BaseModel):
    interpretation: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
