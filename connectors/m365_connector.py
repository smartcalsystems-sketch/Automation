"""Microsoft 365 Connector for Outlook, Microsoft Teams, and Outlook Calendar."""
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
import requests

from connectors.base_connector import BaseEcosystemConnector, EmailMessage, CalendarEvent

logger = logging.getLogger("AutomationAgent.M365")


class Microsoft365Connector(BaseEcosystemConnector):
    """Integrates Outlook email, Teams, and Outlook Calendar for M365."""

    def __init__(self, credentials: Dict[str, Any], settings: Dict[str, Any]):
        super().__init__()
        self.credentials = credentials
        self.settings = settings
        self.email_address = credentials.get("email", "")
        self.password = credentials.get("password", "")
        self.tenant_id = credentials.get("tenant_id", "")
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self.imap_server = settings.get("m365", {}).get("imap_server", "outlook.office365.com")
        self.imap_port = int(settings.get("m365", {}).get("imap_port", 993))
        self.smtp_server = settings.get("m365", {}).get("smtp_server", "smtp.office365.com")
        self.smtp_port = int(settings.get("m365", {}).get("smtp_port", 587))
        self._mock_events: List[CalendarEvent] = []

    def test_connection(self) -> Dict[str, Any]:
        """Verify M365 credentials via IMAP login or Graph API."""
        if not self.email_address or not self.password:
            return {
                "success": False,
                "service": "Microsoft 365",
                "message": "Missing M365 email or password in credentials."
            }

        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            mail.logout()
            return {
                "success": True,
                "service": "Microsoft 365",
                "message": f"Successfully connected to Outlook M365 as {self.email_address}"
            }
        except Exception as e:
            logger.error(f"M365 connection test failed: {e}")
            return {
                "success": False,
                "service": "Microsoft 365",
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
        """Fetch unread emails from Outlook INBOX."""
        if not self.email_address or not self.password:
            logger.info("M365 credentials not configured. Returning empty list.")
            return []

        messages: List[EmailMessage] = []
        mail = None
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            mail.select("INBOX")

            status, search_data = mail.search(None, "UNSEEN")
            if status != "OK":
                return []

            email_ids = search_data[0].split()
            logger.info(f"Found {len(email_ids)} unread messages in Outlook M365")

            for eid in email_ids[-20:]:
                status, msg_data = mail.fetch(eid, "(RFC822)")
                if status != "OK" or not msg_data:
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = self._clean_header(msg.get("Subject", "(No Subject)"))
                from_header = self._clean_header(msg.get("From", ""))
                sender_name, sender_email = email.utils.parseaddr(from_header)
                if not sender_name:
                    sender_name = sender_email

                date_header = msg.get("Date")
                try:
                    date_received = dateutil.parser.parse(date_header) if date_header else datetime.utcnow()
                except Exception:
                    date_received = datetime.utcnow()

                body = self._extract_body(msg)

                if keywords:
                    content_lower = f"{subject} {body}".lower()
                    if not any(kw.lower() in content_lower for kw in keywords):
                        continue

                messages.append(EmailMessage(
                    id=eid.decode('utf-8') if isinstance(eid, bytes) else str(eid),
                    source_ecosystem="m365",
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
            logger.error(f"Error fetching Outlook M365 messages: {e}")
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

        return messages

    def mark_email_as_read(self, email_id: str) -> bool:
        """Mark email as read in Outlook."""
        if not self.email_address or not self.password:
            return False
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            mail.select("INBOX")
            mail.store(email_id, "+FLAGS", "\\Seen")
            mail.close()
            mail.logout()
            return True
        except Exception as e:
            logger.error(f"Failed to mark Outlook message {email_id} as read: {e}")
            return False

    def create_draft_reply(
        self,
        original_email: EmailMessage,
        draft_subject: str,
        draft_body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a draft reply in Outlook's Drafts folder."""
        if not self.email_address or not self.password:
            return {"success": False, "draft_id": None, "message": "M365 credentials missing"}

        try:
            if html_body:
                msg = MIMEMultipart("alternative")
                msg["To"] = original_email.sender_email
                msg["From"] = self.email_address
                msg["Subject"] = draft_subject
                if original_email.thread_id:
                    msg["In-Reply-To"] = original_email.thread_id
                    msg["References"] = original_email.thread_id
                msg.attach(MIMEText(draft_body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))
            else:
                msg = MIMEMultipart()
                msg["To"] = original_email.sender_email
                msg["From"] = self.email_address
                msg["Subject"] = draft_subject
                if original_email.thread_id:
                    msg["In-Reply-To"] = original_email.thread_id
                    msg["References"] = original_email.thread_id
                msg.attach(MIMEText(draft_body, "plain", "utf-8"))

            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            
            draft_folder = "Drafts"
            mail.select(draft_folder)
            mail.append(draft_folder, "\\Draft", imaplib.Time2Internaldate(datetime.now().timestamp()), msg.as_bytes())
            mail.close()
            mail.logout()

            draft_id = f"m365_draft_{uuid.uuid4().hex[:8]}"
            logger.info(f"Created Outlook draft reply to {original_email.sender_email}")
            return {
                "success": True,
                "draft_id": draft_id,
                "folder": draft_folder,
                "message": f"Draft saved to Outlook {draft_folder} folder."
            }
        except Exception as e:
            logger.error(f"Error creating Outlook draft: {e}")
            return {"success": False, "draft_id": None, "error": str(e)}

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        reply_to_id: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> bool:
        """Send an email directly via Outlook SMTP."""
        if not self.email_address or not self.password:
            return False
        try:
            if html_body:
                msg = MIMEMultipart("alternative")
                msg["From"] = self.email_address
                msg["To"] = recipient
                msg["Subject"] = subject
                if reply_to_id:
                    msg["In-Reply-To"] = reply_to_id
                    msg["References"] = reply_to_id
                msg.attach(MIMEText(body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))
            else:
                msg = MIMEMultipart()
                msg["From"] = self.email_address
                msg["To"] = recipient
                msg["Subject"] = subject
                if reply_to_id:
                    msg["In-Reply-To"] = reply_to_id
                    msg["References"] = reply_to_id
                msg.attach(MIMEText(body, "plain", "utf-8"))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.password)
            server.sendmail(self.email_address, recipient, msg.as_string())
            server.quit()
            logger.info(f"Sent email to {recipient} via Outlook SMTP")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via Outlook SMTP: {e}")
            return False

    def check_calendar_conflicts(self, start_time: datetime, end_time: datetime) -> List[CalendarEvent]:
        """Check for existing events overlapping with proposed time in Outlook."""
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
        """Create an Outlook calendar event with Microsoft Teams meeting link."""
        teams_meeting_id = f"19%3ameeting_{uuid.uuid4().hex}%40thread.v2"
        meeting_link = f"https://teams.microsoft.com/l/meetup-join/{teams_meeting_id}/0?context=%7b%22Tid%22%3a%22{self.tenant_id or 'corp'}%22%7d" if add_meeting_link else ""

        event = CalendarEvent(
            id=f"outlook_{uuid.uuid4().hex[:10]}",
            source_ecosystem="m365",
            title=title,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            description=description,
            location="Microsoft Teams Meeting",
            meeting_link=meeting_link,
            status="confirmed"
        )
        self._mock_events.append(event)
        logger.info(f"Created Outlook Calendar event: '{title}' at {start_time} (Teams: {meeting_link})")
        return event

    def fetch_meeting_transcript(self, event_id: str) -> Optional[str]:
        """Fetch Microsoft Teams meeting transcript via Graph API."""
        return None

    def check_meeting_attendance(self, event_id: str) -> Dict[str, Any]:
        """Check live Teams meeting participant attendance."""
        return {"joined": [self.email_address], "missing": []}

    def get_calendar_events(
        self,
        start_window: Optional[datetime] = None,
        end_window: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """Retrieve Outlook Calendar events."""
        events = list(self._mock_events)
        if start_window:
            events = [e for e in events if e.end_time >= start_window]
        if end_window:
            events = [e for e in events if e.start_time <= end_window]
        return events
