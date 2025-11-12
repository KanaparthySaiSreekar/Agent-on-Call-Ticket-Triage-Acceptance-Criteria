"""
Script to seed the database with sample tickets for testing.

This creates at least 3 tickets with different intents to demonstrate
varied triage decisions.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import init_db, AsyncSessionLocal
from backend.models import Ticket, TicketStatus


SAMPLE_TICKETS = [
    {
        "title": "🚨 CRITICAL: Production database is down - all users affected",
        "description": """Our production database cluster has completely crashed and none of our users can access the application.
        We're seeing connection timeout errors across all services. This started about 15 minutes ago and is affecting
        thousands of active users. We need immediate assistance to restore service. Error logs show:
        'ERROR: could not connect to server: Connection refused'""",
        "customer_email": "ops-team@acmecorp.com",
        "tags": ["database", "production", "critical", "outage"],
        "expected_priority": "P0",
        "expected_assignee": "Bob Martinez"
    },
    {
        "title": "Users unable to login with Google OAuth",
        "description": """Several customers have reported that they cannot log in using the 'Sign in with Google' button.
        The button appears to work, redirects to Google, but then fails with an 'Authentication Error' message when
        returning to our site. Regular email/password login works fine. This started after yesterday's deployment.
        Approximately 30% of our users prefer Google login.""",
        "customer_email": "support@startup.io",
        "tags": ["authentication", "oauth", "login", "google"],
        "expected_priority": "P1",
        "expected_assignee": "Alice Chen"
    },
    {
        "title": "Invoice download button has wrong styling",
        "description": """Hi team, I noticed that the 'Download Invoice' button on the billing page is using a different
        color scheme than the rest of the UI. It's currently blue instead of our brand purple. It works fine functionally,
        but it looks inconsistent with our design system. Would be great to fix this when you have a chance.
        Not urgent, just a polish item for the next release.""",
        "customer_email": "design@company.com",
        "tags": ["ui", "design", "billing", "cosmetic"],
        "expected_priority": "P3",
        "expected_assignee": "Carol Johnson"
    },
    {
        "title": "API rate limiting not working as expected",
        "description": """We've integrated with your REST API and noticed that the rate limiting headers don't seem to
        match the documented behavior. According to docs, we should get 100 requests per minute, but we're being
        throttled after about 75 requests. The X-RateLimit-Remaining header also shows inconsistent values.
        This is affecting our integration tests and causing some automation failures.""",
        "customer_email": "devops@partner.com",
        "tags": ["api", "rate-limiting", "integration", "documentation"],
        "expected_priority": "P2",
        "expected_assignee": "David Kim"
    },
    {
        "title": "Question about upgrading subscription plan",
        "description": """Hello! I'm currently on the Starter plan and interested in upgrading to the Professional plan.
        I have a few questions: (1) Will I be charged immediately or at the end of my current billing cycle?
        (2) Can I downgrade later if needed? (3) What happens to my current data and settings?
        I'd appreciate clarification before I make the change. Thanks!""",
        "customer_email": "customer@smallbiz.com",
        "tags": ["billing", "subscription", "question", "upgrade"],
        "expected_priority": "P2",
        "expected_assignee": "Emma Wilson"
    },
    {
        "title": "Not receiving email notifications for comments",
        "description": """I have email notifications enabled in my account settings, but I'm not receiving emails when
        someone comments on my posts. I've checked my spam folder and email is correct. Other notifications
        (like password resets) work fine. Just the comment notifications seem broken. Using Gmail if that matters.""",
        "customer_email": "user@gmail.com",
        "tags": ["email", "notifications", "comments"],
        "expected_priority": "P2",
        "expected_assignee": "Frank Zhang"
    }
]


async def seed_tickets():
    """Create sample tickets in the database."""
    print("🌱 Seeding sample tickets...")
    print("=" * 60)

    # Initialize database
    await init_db()

    async with AsyncSessionLocal() as session:
        created_count = 0

        for idx, ticket_data in enumerate(SAMPLE_TICKETS, 1):
            # Extract expected values (not part of model)
            expected_priority = ticket_data.pop("expected_priority", None)
            expected_assignee = ticket_data.pop("expected_assignee", None)

            # Create ticket
            ticket = Ticket(
                **ticket_data,
                status=TicketStatus.OPEN.value
            )

            session.add(ticket)
            await session.flush()  # Get the ID

            print(f"\n[{idx}] Created Ticket #{ticket.id}")
            print(f"    Title: {ticket.title[:60]}...")
            print(f"    Tags: {', '.join(ticket.tags)}")
            print(f"    Expected Priority: {expected_priority}")
            print(f"    Expected Assignee: {expected_assignee}")

            created_count += 1

        await session.commit()

    print("\n" + "=" * 60)
    print(f"✅ Successfully created {created_count} sample tickets!")
    print("\nThese tickets demonstrate different scenarios:")
    print("  • P0: Critical production outage")
    print("  • P1: Core functionality broken (OAuth login)")
    print("  • P2: Medium priority issues (API, billing, notifications)")
    print("  • P3: Low priority cosmetic issues")
    print("\nStart the server and use the auto-triage feature to see AI-powered")
    print("priority assignment, assignee suggestions, and reply drafts!")


if __name__ == "__main__":
    asyncio.run(seed_tickets())
