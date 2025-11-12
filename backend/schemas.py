"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


# Ticket Schemas
class TicketBase(BaseModel):
    """Base ticket schema."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    customer_email: EmailStr
    tags: List[str] = Field(default_factory=list)


class TicketCreate(TicketBase):
    """Schema for creating a ticket."""
    pass


class TicketUpdate(BaseModel):
    """Schema for updating a ticket."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None


# Triage Result Schemas
class TriageResultResponse(BaseModel):
    """Schema for triage result response."""
    id: int
    ticket_id: int
    suggested_priority: str
    priority_confidence: float
    priority_rationale: str
    suggested_assignee: Optional[str]
    assignee_rationale: Optional[str]
    reply_draft: str
    triaged_at: datetime
    triage_duration_ms: Optional[int]

    class Config:
        from_attributes = True


# Activity Log Schemas
class ActivityLogResponse(BaseModel):
    """Schema for activity log response."""
    id: int
    ticket_id: int
    action_type: str
    actor: str
    description: str
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# Ticket Response Schema
class TicketResponse(BaseModel):
    """Schema for ticket response."""
    id: int
    title: str
    description: str
    customer_email: str
    status: str
    priority: Optional[str]
    assigned_to: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    triage_result: Optional[TriageResultResponse] = None
    activity_logs: List[ActivityLogResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


# Triage Request Schema
class TriageRequest(BaseModel):
    """Schema for triggering triage on a ticket."""
    ticket_id: int


class TriageResponse(BaseModel):
    """Schema for triage operation response."""
    success: bool
    message: str
    triage_result: Optional[TriageResultResponse] = None
    error: Optional[str] = None


# Reply Draft Schemas
class ReplyDraftUpdate(BaseModel):
    """Schema for updating/accepting a reply draft."""
    reply_text: str
    accepted: bool = True


class ReplyDraftResponse(BaseModel):
    """Schema for reply draft save response."""
    success: bool
    message: str
    ticket_id: int
