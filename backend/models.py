"""Database models for the helpdesk system."""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class PriorityLevel(str, Enum):
    """Ticket priority levels."""
    P0 = "P0"  # Critical
    P1 = "P1"  # High
    P2 = "P2"  # Medium
    P3 = "P3"  # Low


class TicketStatus(str, Enum):
    """Ticket status values."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Ticket(Base):
    """Main ticket model."""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    customer_email = Column(String(255), nullable=False)
    status = Column(String(50), default=TicketStatus.OPEN.value)
    priority = Column(String(10), nullable=True)
    assigned_to = Column(String(255), nullable=True)
    tags = Column(JSON, default=list)  # List of tags for categorization
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    triage_result = relationship("TriageResult", back_populates="ticket", uselist=False, cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="ticket", cascade="all, delete-orphan")


class TriageResult(Base):
    """Stores AI triage results for a ticket."""
    __tablename__ = "triage_results"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), unique=True, nullable=False)

    # Priority assignment
    suggested_priority = Column(String(10), nullable=False)
    priority_confidence = Column(Float, nullable=False)
    priority_rationale = Column(Text, nullable=False)

    # Assignee suggestion
    suggested_assignee = Column(String(255), nullable=True)
    assignee_rationale = Column(Text, nullable=True)

    # First reply draft
    reply_draft = Column(Text, nullable=False)

    # Metadata
    triaged_at = Column(DateTime, default=datetime.utcnow)
    triage_duration_ms = Column(Integer, nullable=True)

    # Relationships
    ticket = relationship("Ticket", back_populates="triage_result")


class ActivityLog(Base):
    """Activity history for tickets."""
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    action_type = Column(String(50), nullable=False)  # created, triaged, updated, commented, etc.
    actor = Column(String(255), nullable=False)  # Who performed the action
    description = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)  # Additional context

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship("Ticket", back_populates="activity_logs")
