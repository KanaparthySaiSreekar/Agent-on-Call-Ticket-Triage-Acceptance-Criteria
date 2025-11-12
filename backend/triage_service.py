"""AI-powered triage service using Anthropic Claude."""
import asyncio
import json
import os
import time
from typing import Dict, Any, Optional
from anthropic import AsyncAnthropic


class TriageService:
    """Service for AI-powered ticket triage."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 5):
        """Initialize triage service with Anthropic client."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.timeout = timeout
        self.max_reply_words = int(os.getenv("MAX_REPLY_WORDS", "120"))

        # Sample team members with their expertise
        self.team_members = {
            "Alice Chen": ["authentication", "security", "login", "password", "2fa", "oauth"],
            "Bob Martinez": ["database", "performance", "slow", "query", "connection", "sql"],
            "Carol Johnson": ["ui", "interface", "design", "display", "layout", "css", "frontend"],
            "David Kim": ["api", "integration", "webhook", "rest", "graphql", "backend"],
            "Emma Wilson": ["billing", "payment", "invoice", "subscription", "charge", "pricing"],
            "Frank Zhang": ["email", "notification", "alert", "message", "sms", "communication"],
        }

    async def triage_ticket(
        self,
        ticket_id: int,
        title: str,
        description: str,
        customer_email: str,
        tags: list = None
    ) -> Dict[str, Any]:
        """
        Perform AI triage on a ticket.

        Returns:
            Dict with priority, assignee, and reply draft information
        """
        start_time = time.time()

        try:
            # Create a comprehensive prompt for triage
            prompt = self._build_triage_prompt(title, description, customer_email, tags or [])

            # Call Claude API with timeout
            response = await asyncio.wait_for(
                self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1500,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                ),
                timeout=self.timeout
            )

            # Parse the response
            result = self._parse_triage_response(response.content[0].text)

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            result["triage_duration_ms"] = duration_ms

            return result

        except asyncio.TimeoutError:
            raise TimeoutError(f"Triage operation exceeded {self.timeout} seconds")
        except Exception as e:
            raise Exception(f"Triage failed: {str(e)}")

    def _build_triage_prompt(
        self,
        title: str,
        description: str,
        customer_email: str,
        tags: list
    ) -> str:
        """Build the prompt for Claude to perform triage."""
        team_info = "\n".join([
            f"- {name}: Expert in {', '.join(skills)}"
            for name, skills in self.team_members.items()
        ])

        return f"""You are a helpdesk triage assistant. Analyze the following support ticket and provide a structured triage response.

**Ticket Details:**
Title: {title}
Description: {description}
Customer Email: {customer_email}
Tags: {', '.join(tags) if tags else 'None'}

**Available Team Members:**
{team_info}

**Your Task:**
Provide a JSON response with the following structure:

{{
  "priority": "P0 or P1 or P2 or P3",
  "priority_confidence": 0.0-1.0,
  "priority_rationale": "Brief explanation (1-2 sentences)",
  "suggested_assignee": "Name from team list or null",
  "assignee_rationale": "Why this person is best suited (1 sentence) or null",
  "reply_draft": "Professional first reply to customer (max {self.max_reply_words} words)"
}}

**Priority Guidelines:**
- P0 (Critical): System down, data loss, security breach, many users affected
- P1 (High): Core functionality broken, significant business impact, urgent
- P2 (Medium): Feature not working, moderate impact, workaround available
- P3 (Low): Minor issue, cosmetic, question, feature request

**Reply Draft Requirements:**
- Acknowledge the issue
- Show empathy
- Indicate next steps
- Be professional and concise (≤ {self.max_reply_words} words)
- Reference specific ticket details

Respond ONLY with valid JSON, no additional text."""

    def _parse_triage_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's response into structured data."""
        try:
            # Extract JSON from response (in case there's extra text)
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start_idx:end_idx]
            result = json.loads(json_str)

            # Validate required fields
            required_fields = [
                "priority",
                "priority_confidence",
                "priority_rationale",
                "reply_draft"
            ]

            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")

            # Validate priority level
            if result["priority"] not in ["P0", "P1", "P2", "P3"]:
                raise ValueError(f"Invalid priority: {result['priority']}")

            # Validate confidence
            confidence = float(result["priority_confidence"])
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"Invalid confidence: {confidence}")

            # Ensure assignee_rationale is None if no assignee
            if not result.get("suggested_assignee"):
                result["suggested_assignee"] = None
                result["assignee_rationale"] = None

            return result

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse triage response: {str(e)}")
