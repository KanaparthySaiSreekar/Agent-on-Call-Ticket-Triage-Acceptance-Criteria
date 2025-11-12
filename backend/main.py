"""Main FastAPI application for helpdesk auto-triage system."""
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import init_db, get_db
from backend.models import Ticket, TriageResult, ActivityLog, TicketStatus, PriorityLevel
from backend.schemas import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TriageRequest,
    TriageResponse,
    TriageResultResponse,
    ReplyDraftUpdate,
    ReplyDraftResponse,
)
from backend.triage_service import TriageService
import os


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


# Create FastAPI app
app = FastAPI(
    title="Helpdesk Auto-Triage API",
    description="AI-powered helpdesk ticket triage system with automatic priority assignment, assignee suggestions, and reply drafts",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize triage service
triage_service = TriageService()


# Ticket CRUD Endpoints
@app.post("/api/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new helpdesk ticket."""
    ticket = Ticket(
        title=ticket_data.title,
        description=ticket_data.description,
        customer_email=ticket_data.customer_email,
        tags=ticket_data.tags,
        status=TicketStatus.OPEN.value,
    )

    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    # Create activity log
    activity = ActivityLog(
        ticket_id=ticket.id,
        action_type="created",
        actor="system",
        description=f"Ticket created by {ticket_data.customer_email}",
        metadata={"title": ticket_data.title}
    )
    db.add(activity)
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket.id)
        .options(
            selectinload(Ticket.triage_result),
            selectinload(Ticket.activity_logs)
        )
    )
    ticket = result.scalar_one()

    return ticket


@app.get("/api/tickets", response_model=List[TicketResponse])
async def list_tickets(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all tickets with optional filters."""
    query = select(Ticket).options(
        selectinload(Ticket.triage_result),
        selectinload(Ticket.activity_logs)
    ).order_by(desc(Ticket.created_at))

    if status_filter:
        query = query.where(Ticket.status == status_filter)
    if priority_filter:
        query = query.where(Ticket.priority == priority_filter)

    result = await db.execute(query)
    tickets = result.scalars().all()

    return tickets


@app.get("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific ticket by ID."""
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.triage_result),
            selectinload(Ticket.activity_logs)
        )
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    return ticket


@app.put("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a ticket."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    # Track changes for activity log
    changes = []

    update_data = ticket_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        old_value = getattr(ticket, field)
        if old_value != value:
            setattr(ticket, field, value)
            changes.append(f"{field}: {old_value} → {value}")

    if changes:
        ticket.updated_at = datetime.utcnow()

        # Create activity log
        activity = ActivityLog(
            ticket_id=ticket.id,
            action_type="updated",
            actor="user",
            description=f"Ticket updated: {', '.join(changes)}",
            metadata=update_data
        )
        db.add(activity)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.triage_result),
            selectinload(Ticket.activity_logs)
        )
    )
    ticket = result.scalar_one()

    return ticket


@app.delete("/api/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a ticket."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    await db.delete(ticket)
    await db.commit()


# Triage Endpoints
@app.post("/api/triage", response_model=TriageResponse)
async def triage_ticket(
    triage_request: TriageRequest,
    db: AsyncSession = Depends(get_db)
):
    """Trigger AI-powered triage on a ticket."""
    ticket_id = triage_request.ticket_id

    # Get ticket
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    try:
        # Perform AI triage with timeout
        triage_result = await triage_service.triage_ticket(
            ticket_id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            customer_email=ticket.customer_email,
            tags=ticket.tags or []
        )

        # Delete existing triage result if any
        existing_result = await db.execute(
            select(TriageResult).where(TriageResult.ticket_id == ticket_id)
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            await db.delete(existing)
            await db.flush()

        # Create new triage result
        new_triage = TriageResult(
            ticket_id=ticket_id,
            suggested_priority=triage_result["priority"],
            priority_confidence=triage_result["priority_confidence"],
            priority_rationale=triage_result["priority_rationale"],
            suggested_assignee=triage_result.get("suggested_assignee"),
            assignee_rationale=triage_result.get("assignee_rationale"),
            reply_draft=triage_result["reply_draft"],
            triage_duration_ms=triage_result.get("triage_duration_ms")
        )

        db.add(new_triage)

        # Update ticket with suggested values
        ticket.priority = triage_result["priority"]
        ticket.assigned_to = triage_result.get("suggested_assignee")
        ticket.updated_at = datetime.utcnow()

        # Create activity log
        activity = ActivityLog(
            ticket_id=ticket_id,
            action_type="triaged",
            actor="ai_system",
            description=f"Auto-triaged as {triage_result['priority']} and assigned to {triage_result.get('suggested_assignee', 'unassigned')}",
            metadata={
                "confidence": triage_result["priority_confidence"],
                "duration_ms": triage_result.get("triage_duration_ms")
            }
        )
        db.add(activity)

        await db.commit()
        await db.refresh(new_triage)

        return TriageResponse(
            success=True,
            message="Ticket triaged successfully",
            triage_result=TriageResultResponse.model_validate(new_triage)
        )

    except TimeoutError as e:
        return TriageResponse(
            success=False,
            message="Triage operation timed out",
            error=str(e)
        )
    except Exception as e:
        return TriageResponse(
            success=False,
            message="Triage operation failed",
            error=str(e)
        )


@app.post("/api/tickets/{ticket_id}/reply", response_model=ReplyDraftResponse)
async def save_reply_draft(
    ticket_id: int,
    reply_update: ReplyDraftUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Accept or edit a reply draft."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    # Create activity log for reply
    action = "accepted" if reply_update.accepted else "edited"
    activity = ActivityLog(
        ticket_id=ticket_id,
        action_type="reply_saved",
        actor="user",
        description=f"Reply draft {action} and saved",
        metadata={
            "reply_text": reply_update.reply_text[:100] + "..." if len(reply_update.reply_text) > 100 else reply_update.reply_text,
            "accepted": reply_update.accepted
        }
    )
    db.add(activity)
    await db.commit()

    return ReplyDraftResponse(
        success=True,
        message=f"Reply draft {action} successfully",
        ticket_id=ticket_id
    )


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "helpdesk-auto-triage"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
