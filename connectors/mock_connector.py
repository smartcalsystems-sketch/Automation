"""Simulation & offline testing connector for Google Workspace and Microsoft 365.

Provides realistic enterprise email streams and calendar events covering all 4 pillars:
Cross-account conflicts, slot negotiation, urgent escalations, deliverables, OOO, and invoices.
"""
from datetime import datetime, timedelta
import uuid
from typing import List, Optional, Dict, Any
from connectors.base_connector import BaseEcosystemConnector, EmailMessage, CalendarEvent


class MockEcosystemConnector(BaseEcosystemConnector):
    """High-fidelity simulation connector supporting both Google and M365 ecosystems."""

    def __init__(self, ecosystem: str = "google"):
        super().__init__()
        self.ecosystem = ecosystem
        now = datetime.utcnow()
        # Seed realistic incoming unread emails
        self._unread_emails: List[EmailMessage] = self._generate_sample_emails(now)
        
        concluded_event_id = f"{self.ecosystem}_event_concluded_mom"
        active_noshow_id = f"{self.ecosystem}_event_active_noshow"

        # Calendar events: Pre-existing event + upcoming event in 20 min + concluded event + active no-show event
        self._calendar_events: List[CalendarEvent] = [
            CalendarEvent(
                id=f"{self.ecosystem}_event_pre_existing",
                source_ecosystem=self.ecosystem,
                title="Weekly Engineering All-Hands",
                start_time=now.replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=1),
                end_time=now.replace(hour=16, minute=0, second=0, microsecond=0) + timedelta(days=1),
                attendees=["engineering-team@company.internal"],
                description="Weekly sprint demo and sync",
                location="Google Meet" if ecosystem == "google" else "Microsoft Teams",
                meeting_link="https://meet.google.com/eng-allhands" if ecosystem == "google" else "https://teams.microsoft.com/l/meetup-join/allhands",
                status="confirmed"
            ),
            CalendarEvent(
                id=f"{self.ecosystem}_event_upcoming_dossier",
                source_ecosystem=self.ecosystem,
                title="Strategic Partner Sync with Acme Partners",
                start_time=now + timedelta(minutes=20),
                end_time=now + timedelta(minutes=50),
                attendees=["sarah.jenkins@acmepartners.com"],
                description="Discussion regarding Q4 Cloud Integration patterns.",
                location="Google Meet" if ecosystem == "google" else "Microsoft Teams",
                meeting_link="https://meet.google.com/dossier-sync",
                status="confirmed"
            ),
            CalendarEvent(
                id=concluded_event_id,
                source_ecosystem=self.ecosystem,
                title="Q4 Cloud Architecture & Security Review",
                start_time=now - timedelta(minutes=45),
                end_time=now - timedelta(minutes=5),
                attendees=["sarah.jenkins@acmepartners.com", "david.chen@enterprise365.net"],
                description="Final review of cloud security architecture and rollout schedule.",
                location="Google Meet" if ecosystem == "google" else "Microsoft Teams",
                meeting_link="https://meet.google.com/q4-security" if ecosystem == "google" else "https://teams.microsoft.com/l/meetup-join/q4-sec",
                status="confirmed"
            ),
            CalendarEvent(
                id=active_noshow_id,
                source_ecosystem=self.ecosystem,
                title="Client Success Onboarding Sync",
                start_time=now - timedelta(minutes=8),
                end_time=now + timedelta(minutes=22),
                attendees=["marcus.vance@techscale.io"],
                description="Live customer onboarding walkthrough session.",
                location="Google Meet" if ecosystem == "google" else "Microsoft Teams",
                meeting_link="https://meet.google.com/live-sync" if ecosystem == "google" else "https://teams.microsoft.com/l/meetup-join/live-sync",
                status="confirmed"
            )
        ]

        self._transcripts: Dict[str, str] = {
            concluded_event_id: (
                "Sarah Jenkins (00:02): Good afternoon everyone. Let's finalize the Q4 cloud security deliverables.\n"
                "David Chen (00:15): I agree. Key decision: We decided to enforce AES-256 for all at-rest credentials.\n"
                "Sarah Jenkins (00:30): Perfect. Action item: Sarah will deliver the updated Terraform scripts by Friday EOD.\n"
                "David Chen (00:45): And I will complete the security audit report before Monday morning.\n"
                "Sarah Jenkins (01:00): Excellent, meeting adjourned."
            )
        }
        self._attendance_records: Dict[str, Dict[str, Any]] = {
            active_noshow_id: {
                "joined": ["internal-host@company.internal"],
                "missing": ["marcus.vance@techscale.io"]
            }
        }
        self._drafts_created: List[Dict[str, Any]] = []
        self._sent_emails: List[Dict[str, Any]] = []

    def _generate_sample_emails(self, now: datetime) -> List[EmailMessage]:
        if self.ecosystem == "google":
            target_date_1 = (now + timedelta(days=1)).strftime("%B %d, %Y at 2:00 PM UTC")
            return [
                EmailMessage(
                    id=f"gmail_{uuid.uuid4().hex[:8]}",
                    source_ecosystem="google",
                    sender_name="Sarah Jenkins",
                    sender_email="sarah.jenkins@acmepartners.com",
                    subject="Q4 Strategic Cloud Integration & Architecture Review",
                    date_received=now - timedelta(minutes=25),
                    body_text=(
                        f"Hi Team,\n\n"
                        f"Following our recent kickoff discussion, I would love to schedule a dedicated architecture review "
                        f"session to finalize the cloud API integration patterns and data retention pipelines.\n\n"
                        f"Could we meet on {target_date_1} for 45 minutes?\n\n"
                        f"Key action items for our agenda:\n"
                        f"- Review latency benchmarks and rate-limiting thresholds\n"
                        f"- Finalize OAuth credential rotation and vault policies\n"
                        f"- Confirm deployment milestones for staging and production\n\n"
                        f"Please send over a Google Meet invite if that time slot works for you.\n\n"
                        f"Best regards,\n"
                        f"Sarah Jenkins\n"
                        f"Director of Solutions Architecture | Acme Partners"
                    )
                ),
                EmailMessage(
                    id=f"gmail_{uuid.uuid4().hex[:8]}",
                    source_ecosystem="google",
                    sender_name="Alex Rivera",
                    sender_email="alex.rivera@fintechglobal.org",
                    subject="CRITICAL EMERGENCY: Urgent Database Failover Required ASAP",
                    date_received=now - timedelta(minutes=5),
                    body_text=(
                        f"URGENT ATTENTION REQUIRED:\n\n"
                        f"We are observing intermittent timeouts on the production authentication gateway. "
                        f"This is an emergency incident requiring immediate remediation.\n\n"
                        f"Please investigate and confirm system failover status immediately."
                    )
                ),
                EmailMessage(
                    id=f"gmail_{uuid.uuid4().hex[:8]}",
                    source_ecosystem="google",
                    sender_name="Marcus Vance",
                    sender_email="marcus.vance@techscale.io",
                    subject="Deliverable Commitment: Final Cloud Architecture Deck",
                    date_received=now - timedelta(minutes=2),
                    body_text=(
                        f"Hi Team,\n\n"
                        f"I will share the architecture deck by Friday EOD for the executive review.\n\n"
                        f"Action items:\n"
                        f"- Complete load-balancer topology diagrams\n"
                        f"- Benchmark microservice response times\n\n"
                        f"Regards,\nMarcus"
                    )
                ),
                EmailMessage(
                    id=f"gmail_{uuid.uuid4().hex[:8]}",
                    source_ecosystem="google",
                    sender_name="Accounts Payable",
                    sender_email="billing@cloudservices.com",
                    subject="Invoice #INV-2026-904 from CloudServices Inc",
                    date_received=now - timedelta(minutes=1),
                    body_text=(
                        f"Dear Customer,\n\n"
                        f"Please find your monthly infrastructure statement:\n"
                        f"Vendor: CloudServices Inc\n"
                        f"Invoice Number: INV-2026-904\n"
                        f"Amount Due: $4,850.00 USD\n"
                        f"Payment Due Date: October 25, 2026\n\n"
                        f"Thank you for your business."
                    )
                )
            ]
        else:
            # Microsoft 365: Meeting proposing slot that conflicts with All-Hands (15:15 tomorrow)
            conflict_slot = (now + timedelta(days=1)).strftime("%B %d, %Y at 3:15 PM UTC")
            return [
                EmailMessage(
                    id=f"outlook_{uuid.uuid4().hex[:8]}",
                    source_ecosystem="m365",
                    sender_name="David Chen",
                    sender_email="dchen@enterprise365.net",
                    subject="Executive Sync: Microsoft 365 Architecture",
                    date_received=now - timedelta(minutes=45),
                    body_text=(
                        f"Good morning,\n\n"
                        f"Let's schedule a working session on {conflict_slot} for 45 minutes.\n\n"
                        f"Agenda items:\n"
                        f"- Walk through Microsoft Teams meeting auto-generation logic\n"
                        f"- Review conflict resolution policies for executive calendars\n\n"
                        f"Regards,\nDavid Chen"
                    )
                ),
                EmailMessage(
                    id=f"outlook_{uuid.uuid4().hex[:8]}",
                    source_ecosystem="m365",
                    sender_name="Emily Zhao",
                    sender_email="emily.zhao@venturecap.com",
                    subject="Out of Office: Emily Zhao on Annual Leave",
                    date_received=now - timedelta(minutes=10),
                    body_text=(
                        f"Hello,\n\n"
                        f"I am currently out of office on annual leave with limited access to email.\n"
                        f"I will be returning to the office on October 15, 2026.\n\n"
                        f"For urgent queries, please contact team@venturecap.com.\n\n"
                        f"Best regards,\nEmily Zhao"
                    )
                )
            ]

    def test_connection(self) -> Dict[str, Any]:
        return {
            "success": True,
            "service": f"Simulated {self.ecosystem.upper()}",
            "message": f"Connected to high-fidelity {self.ecosystem} sandbox."
        }

    def fetch_unread_emails(self, keywords: Optional[List[str]] = None) -> List[EmailMessage]:
        if not keywords:
            return list(self._unread_emails)
        filtered = []
        for msg in self._unread_emails:
            content = f"{msg.subject} {msg.body_text}".lower()
            if any(kw.lower() in content for kw in keywords):
                filtered.append(msg)
        return filtered

    def mark_email_as_read(self, email_id: str) -> bool:
        self._unread_emails = [m for m in self._unread_emails if m.id != email_id]
        return True

    def create_draft_reply(
        self,
        original_email: EmailMessage,
        draft_subject: str,
        draft_body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        draft_record = {
            "draft_id": f"draft_{uuid.uuid4().hex[:8]}",
            "to": original_email.sender_email,
            "subject": draft_subject,
            "body": draft_body,
            "html_body": html_body,
            "ecosystem": self.ecosystem,
            "created_at": datetime.utcnow().isoformat()
        }
        self._drafts_created.append(draft_record)
        return {
            "success": True,
            "draft_id": draft_record["draft_id"],
            "folder": "Drafts",
            "message": f"Contextual reply draft successfully created in {self.ecosystem.upper()} Drafts."
        }

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        reply_to_id: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> bool:
        self._sent_emails.append({
            "to": recipient,
            "subject": subject,
            "body": body,
            "html_body": html_body,
            "sent_at": datetime.utcnow().isoformat()
        })
        return True

    def check_calendar_conflicts(self, start_time: datetime, end_time: datetime) -> List[CalendarEvent]:
        conflicts = []
        for event in self._calendar_events:
            if not (end_time <= event.start_time or start_time >= event.end_time):
                conflicts.append(event)
        return conflicts

    def create_calendar_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
        description: str,
        add_meeting_link: bool = True
    ) -> CalendarEvent:
        if self.ecosystem == "google":
            meet_id = f"gmeet-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}"
            link = f"https://meet.google.com/{meet_id}" if add_meeting_link else ""
            loc = "Google Meet"
        else:
            link = f"https://teams.microsoft.com/l/meetup-join/{uuid.uuid4().hex}" if add_meeting_link else ""
            loc = "Microsoft Teams Meeting"

        event = CalendarEvent(
            id=f"{self.ecosystem}_{uuid.uuid4().hex[:8]}",
            source_ecosystem=self.ecosystem,
            title=title,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            description=description,
            location=loc,
            meeting_link=link,
            status="confirmed"
        )
        self._calendar_events.append(event)
        return event

    def fetch_meeting_transcript(self, event_id: str) -> Optional[str]:
        """Retrieve simulated transcript for ended event."""
        return self._transcripts.get(event_id)

    def check_meeting_attendance(self, event_id: str) -> Dict[str, Any]:
        """Check live meeting attendance for no-show auto-recovery."""
        return self._attendance_records.get(event_id, {"joined": [], "missing": []})

    def get_calendar_events(
        self,
        start_window: Optional[datetime] = None,
        end_window: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """Filter calendar events within window."""
        events = list(self._calendar_events)
        if start_window:
            events = [e for e in events if e.end_time >= start_window]
        if end_window:
            events = [e for e in events if e.start_time <= end_window]
        return events
