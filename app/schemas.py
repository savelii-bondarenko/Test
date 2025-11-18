from pydantic import BaseModel
from typing import List
from datetime import datetime

class MessageBase(BaseModel):
    role: str
    content: str

class MessageCreate(BaseModel):
    content: str

class MessageResponse(MessageBase):
    id: int
    tokens_used: int
    cost: float
    timestamp: datetime

    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: int
    created_at: datetime
    total_cost: float
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True