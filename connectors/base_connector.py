"""Base connector interface for Email and Calendar integration."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class EmailMessage:
    """Standardized email message representation."""
    id: str
    source_ecosystem: str  # 'google' or 'm365'
    sender_name: str
    sender_email: str
    subject: str
    date_received: datetime
    body_text: str
    is_read: bool = False
    raw_headers: Dict[str, str] = field(default_factory=dict)
    thread_id: Optional[str] = None


@dataclass
class CalendarEvent:
    """Standardized calendar event representation."""
    id: str
    source_ecosystem: str  # 'google' or 'm365'
    title: str
    start_time: datetime
    end_time: datetime
    attendees: List[str]
    description: str
    location: str = ""
    meeting_link: str = ""  # Google Meet or Microsoft Teams link
    status: str = "confirmed"  # 'confirmed', 'tentative', 'conflict'
    created_at: datetime = field(default_factory=datetime.utcnow)


class BaseEcosystemConnector(ABC):
    """Abstract interface for Google Workspace and Microsoft 365 connectors."""

    def __init__(self):
        self.circuit_state: str = "CLOSED"  # "CLOSED", "OPEN", "HALF-OPEN"
        self.failure_count: int = 0
        self.last_failure_time: Optional[datetime] = None
        self.circuit_reason: str = ""

    def trip_circuit(self, reason: str) -> None:
        """Trip circuit breaker into OPEN state due to rate limits or auth failure."""
        self.circuit_state = "OPEN"
        self.circuit_reason = reason
        self.last_failure_time = datetime.utcnow()

    def reset_circuit(self) -> None:
        """Reset circuit breaker to healthy CLOSED state."""
        self.circuit_state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None
        self.circuit_reason = ""

    def is_circuit_open(self, cooldown_seconds: int = 300) -> bool:
        """Check if circuit breaker is currently OPEN."""
        if self.circuit_state != "OPEN":
            return False
        if self.last_failure_time:
            elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
            if elapsed >= cooldown_seconds:
                # Transition to HALF-OPEN for probe
                self.circuit_state = "HALF-OPEN"
                return False
        return True

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Verify credentials and connectivity."""
        pass

    @abstractmethod
    def fetch_unread_emails(self, keywords: Optional[List[str]] = None) -> List[EmailMessage]:
        """Scan and retrieve unread email messages."""
        pass

    @abstractmethod
    def mark_email_as_read(self, email_id: str) -> bool:
        """Mark an email message as processed/read."""
        pass

    @abstractmethod
    def create_draft_reply(
        self,
        original_email: EmailMessage,
        draft_subject: str,
        draft_body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a contextual reply draft in the user's Drafts folder."""
        pass

    @abstractmethod
    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        reply_to_id: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> bool:
        """Directly send an email response."""
        pass

    @abstractmethod
    def check_calendar_conflicts(self, start_time: datetime, end_time: datetime) -> List[CalendarEvent]:
        """Query calendar for overlapping events in the proposed time range."""
        pass

    @abstractmethod
    def create_calendar_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
        description: str,
        add_meeting_link: bool = True
    ) -> CalendarEvent:
        """Create a calendar entry and optionally attach Meet/Teams link."""
        pass

    def fetch_meeting_transcript(self, event_id: str) -> Optional[str]:
        """Retrieve audio/video transcript for a concluded calendar event."""
        return None

    def check_meeting_attendance(self, event_id: str) -> Dict[str, Any]:
        """Check live meeting attendance status for no-show detection."""
        return {"joined": [], "missing": []}

    def get_calendar_events(
        self,
        start_window: Optional[datetime] = None,
        end_window: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """Retrieve list of calendar events within a given time window."""
        return []
