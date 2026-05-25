import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional

class TicketStatus(Enum):
    DRAFT = "draft"
    PENDING = "pending"
    OPEN = "open"
    RESOLVED = "resolved"

class TicketPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SupportTicket:
    ticket_id: str = ""
    created_at: str = ""
    status: str = TicketStatus.DRAFT.value
    priority: str = TicketPriority.MEDIUM.value
    # User info
    user_name: str = ""
    user_email: str = ""
    # Issue info
    category: str = ""
    subject: str = ""
    description: str = ""
    steps_to_reproduce: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    # Resolution
    resolution_notes: str = ""
    conversation_summary: str = ""
    tags: list = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_markdown(self) -> str:
        return f"""# Support Ticket — {self.ticket_id}

**Created:** {self.created_at}
**Priority:** {self.priority.upper()}
**Status:** {self.status.upper()}
**Category:** {self.category}

## Contact
- **Name:** {self.user_name}
- **Email:** {self.user_email}

## Issue
**Subject:** {self.subject}

**Description:**
{self.description}

**Steps to Reproduce:**
{self.steps_to_reproduce}

**Expected:** {self.expected_behavior}
**Actual:** {self.actual_behavior}

## Conversation Summary
{self.conversation_summary}

## Tags
{', '.join(self.tags) if self.tags else 'None'}
"""
