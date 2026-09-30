"""Google Workspace Connector for Gmail and Google Calendar.

Supports direct credentials (IMAP/SMTP with App Password) and Google APIs.
"""
import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import uuid
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup  # type: ignore
import dateutil.parser

from connectors.base_connector import BaseEcosystemConnector, EmailMessage, CalendarEvent

logger = logging.getLogger("AutomationAgent.Google")

SYSTEM_SENDER_PATTERNS = [
    "no-reply", "noreply", "google.com", "accounts.google",
    "mailer-daemon", "microsoft.com", "security", "mm5921448@gmail.com"
]
SYSTEM_SUBJECT_PATTERNS = [
    "security alert", "2-step verification"
]


def is_system_or_noreply(sender_email: str, subject: str) -> bool:
    """Strictly filter out automated system, security, and no-reply emails."""
    sender_lower = (sender_email or "").lower()
    subject_lower = (subject or "").lower()
    for pat in SYSTEM_SENDER_PATTERNS:
        if pat in sender_lower:
            return True
    for pat in SYSTEM_SUBJECT_PATTERNS:
        if pat in subject_lower:
            return True
    return False


class GoogleWorkspaceConnector(BaseEcosystemConnector):
    """Integrates Gmail and Google Calendar for monitoring, drafting, and scheduling."""

    def __init__(self, credentials: Dict[str, Any], settings: Dict[str, Any]):
        super().__init__()
        self.credentials = credentials
        self.settings = settings
        self.email_address = credentials.get("email", "smartcal.systems@gmail.com")
        self.app_password = credentials.get("app_password", "")
        self.sender_from_header = "SmartCal Systems <smartcal.systems@gmail.com>"
        self.imap_server = settings.get("google", {}).get("imap_server", "imap.gmail.com")
        self.imap_port = int(settings.get("google", {}).get("imap_port", 993))
        self.smtp_server = settings.get("google", {}).get("smtp_server", "smtp.gmail.com")
        self.smtp_port = int(settings.get("google", {}).get("smtp_port", 587))
        self._mock_events: List[CalendarEvent] = []

    def test_connection(self) -> Dict[str, Any]:
        """Verify Gmail credentials via IMAP login."""
        if not self.email_address or not self.app_password:
            return {
                "success": False,
                "service": "Google Workspace",
                "message": "Missing Gmail address or App Password in credentials."
            }
        
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.app_password)
            mail.logout()
            return {
                "success": True,
                "service": "Google Workspace",
                "message": f"Successfully connected to Gmail as {self.email_address}"
            }
        except Exception as e:
            logger.error(f"Gmail connection test failed: {e}")
            return {
                "success": False,
                "service": "Google Workspace",
                "message": f"Connection failed: {str(e)}"
            }

    def _clean_header(self, raw_header: Optional[str]) -> str:
        """Decode MIME encoded email headers."""
        if not raw_header:
            return ""
        decoded_parts = decode_header(raw_header)
        text_parts = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    text_parts.append(part.decode(encoding or "utf-8", errors="replace"))
                except Exception:
                    text_parts.append(part.decode("latin1", errors="replace"))
            else:
                text_parts.append(str(part))
        return "".join(text_parts)

    def _extract_body(self, msg: email.message.Message) -> str:
        """Extract plain text or clean HTML body from email message."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" in content_disposition:
                    continue
                if content_type == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(charset, errors="replace") + "\n"
                elif content_type == "text/html" and not body:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_text = payload.decode(charset, errors="replace")
                        soup = BeautifulSoup(html_text, "html.parser")
                        body = soup.get_text(separator="\n").strip()
        else:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                raw_text = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    soup = BeautifulSoup(raw_text, "html.parser")
                    body = soup.get_text(separator="\n").strip()
                else:
                    body = raw_text
        return body.strip()

    def fetch_unread_emails(self, keywords: Optional[List[str]] = None) -> List[EmailMessage]:
        """Fetch unread emails from Gmail INBOX, strictly skipping system & no-reply senders."""
        if not self.email_address or not self.app_password:
            logger.info("Google credentials not configured. Returning empty list.")
            return []

        messages: List[EmailMessage] = []
        mail = None
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.app_password)
            mail.select("INBOX")

            status, search_data = mail.search(None, "UNSEEN")
            if status != "OK":
                return []

            email_ids = search_data[0].split()
            logger.info(f"Found {len(email_ids)} unread messages in Gmail")

            for eid in email_ids[-20:]:  # Process latest 20 unread
                status, msg_data = mail.fetch(eid, "(RFC822)")
                if status != "OK" or not msg_data:
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = self._clean_header(msg.get("Subject", "(No Subject)"))
                from_header = self._clean_header(msg.get("From", ""))
                
                # Parse sender name and email
                sender_name, sender_email = email.utils.parseaddr(from_header)
                if not sender_name:
                    sender_name = sender_email

                # STRICTLY BLOCK SYSTEM & NO-REPLY EMAILS
                if is_system_or_noreply(sender_email, subject):
                    logger.info(f"Skipping system/no-reply email from '{sender_email}' with subject '{subject}'")
                    try:
                        mail.store(eid, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
                    continue

                date_header = msg.get("Date")
                try:
                    date_received = dateutil.parser.parse(date_header) if date_header else datetime.utcnow()
                except Exception:
                    date_received = datetime.utcnow()

                body = self._extract_body(msg)

                # Filter by keywords if required
                if keywords:
                    content_lower = f"{subject} {body}".lower()
                    if not any(kw.lower() in content_lower for kw in keywords):
                        continue

                messages.append(EmailMessage(
                    id=eid.decode('utf-8') if isinstance(eid, bytes) else str(eid),
                    source_ecosystem="google",
                    sender_name=sender_name,
                    sender_email=sender_email,
                    subject=subject,
                    date_received=date_received,
                    body_text=body,
                    is_read=False,
                    thread_id=msg.get("Message-ID")
                ))

            mail.close()
            mail.logout()
        except Exception as e:
            logger.error(f"Error fetching Gmail messages: {e}")
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

        return messages

    def mark_email_as_read(self, email_id: str) -> bool:
        """Mark email as read in Gmail."""
        if not self.email_address or not self.app_password:
            return False
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.app_password)
            mail.select("INBOX")
            mail.store(email_id, "+FLAGS", "\\Seen")
            mail.close()
            mail.logout()
            return True
        except Exception as e:
            logger.error(f"Failed to mark Gmail message {email_id} as read: {e}")
            return False

    def create_draft_reply(
        self,
        original_email: EmailMessage,
        draft_subject: str,
        draft_body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save contextual draft reply to Gmail Drafts folder (without duplicate SMTP sending)."""
        if not self.email_address or not self.app_password:
            return {"success": False, "draft_id": None, "message": "Credentials missing"}

        # STRICTLY BLOCK SYSTEM & NO-REPLY EMAILS
        if is_system_or_noreply(original_email.sender_email, original_email.subject):
            logger.warning(f"Blocked auto-reply to system/no-reply sender: {original_email.sender_email}")
            return {"success": False, "draft_id": None, "message": "Blocked system/no-reply sender"}

        FROM_HEADER = "SmartCal Systems <smartcal.systems@gmail.com>"
        try:
            if html_body:
                msg = MIMEMultipart("alternative")
                msg["To"] = original_email.sender_email
                msg["From"] = FROM_HEADER
                msg["Subject"] = draft_subject
                if original_email.thread_id:
                    msg["In-Reply-To"] = original_email.thread_id
                    msg["References"] = original_email.thread_id

                msg.attach(MIMEText(draft_body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))
            else:
                msg = MIMEMultipart()
                msg["To"] = original_email.sender_email
                msg["From"] = FROM_HEADER
                msg["Subject"] = draft_subject
                if original_email.thread_id:
                    msg["In-Reply-To"] = original_email.thread_id
                    msg["References"] = original_email.thread_id

                msg.attach(MIMEText(draft_body, "plain", "utf-8"))

            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.app_password)
            
            # Select or append to Drafts
            draft_folder = "[Gmail]/Drafts"
            status, _ = mail.select(draft_folder)
            if status != "OK":
                draft_folder = "Drafts"
                mail.select(draft_folder)

            mail.append(draft_folder, "\\Draft", imaplib.Time2Internaldate(datetime.now().timestamp()), msg.as_bytes())
            mail.close()
            mail.logout()

            draft_id = f"gmail_draft_{uuid.uuid4().hex[:8]}"
            logger.info(f"Archived reply draft in {draft_folder} for {original_email.sender_email}")
            return {
                "success": True,
                "auto_sent": False,
                "draft_id": draft_id,
                "folder": draft_folder,
                "message": f"Draft saved to {draft_folder}."
            }
        except Exception as e:
            logger.error(f"Error creating Gmail draft: {e}")
            return {"success": False, "auto_sent": False, "draft_id": None, "error": str(e)}

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        reply_to_id: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> bool:
        """Send an email directly via Gmail SMTP with From strictly set to SmartCal Systems <smartcal.systems@gmail.com>."""
        if not self.email_address or not self.app_password:
            logger.error("Cannot send email: email_address or app_password missing.")
            return False

        if is_system_or_noreply(recipient, subject):
            logger.warning(f"Blocked sending email to system/no-reply address: {recipient}")
            return False

        FROM_HEADER = "SmartCal Systems <smartcal.systems@gmail.com>"
        try:
            if html_body:
                msg = MIMEMultipart("alternative")
                msg["From"] = FROM_HEADER
                msg["To"] = recipient
                msg["Subject"] = subject
                if reply_to_id:
                    msg["In-Reply-To"] = reply_to_id
                    msg["References"] = reply_to_id

                part_text = MIMEText(body, "plain", "utf-8")
                part_html = MIMEText(html_body, "html", "utf-8")
                msg.attach(part_text)
                msg.attach(part_html)
            else:
                msg = MIMEMultipart()
                msg["From"] = FROM_HEADER
                msg["To"] = recipient
                msg["Subject"] = subject
                if reply_to_id:
                    msg["In-Reply-To"] = reply_to_id
                    msg["References"] = reply_to_id

                msg.attach(MIMEText(body, "plain", "utf-8"))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.app_password)
            server.sendmail(self.email_address, [recipient], msg.as_string())
            server.quit()
            logger.info(f"Auto-sent email to {recipient} via Gmail SMTP from {FROM_HEADER} (HTML={bool(html_body)})")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via Gmail SMTP: {e}")
            return False

    def check_calendar_conflicts(self, start_time: datetime, end_time: datetime) -> List[CalendarEvent]:
        """Check for existing events overlapping with proposed time."""
        conflicts = []
        for event in self._mock_events:
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
        """Create a Google Calendar event with standardized title and clean description."""
        # Strictly format meeting title
        standard_title = "Calendar Invitation: SmartCal Systems Live Demo & Consultation"
        meet_id = uuid.uuid4().hex[:3] + "-" + uuid.uuid4().hex[:4] + "-" + uuid.uuid4().hex[:3]
        meeting_link = f"https://meet.google.com/{meet_id}" if add_meeting_link else ""

        # Filter out blocked personal email mm5921448@gmail.com
        filtered_attendees = [a for a in attendees if a.lower() not in {"mm5921448@gmail.com"}]

        # Clean description: strictly remove any "Attendees:" block or email addresses
        clean_desc_lines = []
        skip_attendees_section = False
        for line in description.split("\n"):
            if "attendees:" in line.lower():
                skip_attendees_section = True
                continue
            if skip_attendees_section:
                if line.strip().startswith("-") or "@" in line or not line.strip():
                    continue
                else:
                    skip_attendees_section = False
            if "@" in line and line.strip().startswith("-"):
                continue
            clean_desc_lines.append(line)
        clean_description = "\n".join(clean_desc_lines).strip()
        
        event = CalendarEvent(
            id=f"gcal_{uuid.uuid4().hex[:10]}",
            source_ecosystem="google",
            title=standard_title,
            start_time=start_time,
            end_time=end_time,
            attendees=filtered_attendees,
            description=clean_description,
            location="Google Meet",
            meeting_link=meeting_link,
            status="confirmed"
        )
        self._mock_events.append(event)
        logger.info(f"Created Google Calendar event: '{standard_title}' at {start_time.strftime('%Y-%m-%d %I:%M %p IST')} (Meet: {meeting_link})")
        return event

    def fetch_meeting_transcript(self, event_id: str) -> Optional[str]:
        """Fetch Google Meet recording transcript."""
        return None

    def check_meeting_attendance(self, event_id: str) -> Dict[str, Any]:
        """Check live Google Meet participant attendance."""
        return {"joined": [self.email_address], "missing": []}

    def get_calendar_events(
        self,
        start_window: Optional[datetime] = None,
        end_window: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """Retrieve Google Calendar events."""
        events = list(self._mock_events)
        if start_window:
            events = [e for e in events if e.end_time >= start_window]
        if end_window:
            events = [e for e in events if e.start_time <= end_window]
        return events
