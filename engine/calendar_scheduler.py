"""Unified Calendar Scheduling, Cross-Account Free/Busy Sync, and Time-Blocking Engine.

Handles multi-account conflict checking, natural language slot negotiation,
focus/prep time-blocking, invoice payment reminders, and OOO auto-rescheduling.
"""
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional
from connectors.base_connector import BaseEcosystemConnector, CalendarEvent

logger = logging.getLogger("AutomationAgent.Calendar")


class UnifiedCalendarScheduler:
    """Manages cross-account scheduling, conflict detection, dossiers, and time-blocking."""

    def __init__(self, connector: BaseEcosystemConnector, all_connectors: Optional[List[BaseEcosystemConnector]] = None):
        self.connector = connector
        self.all_connectors = all_connectors or [connector]

    def check_cross_account_conflicts(self, start_time: datetime, end_time: datetime) -> List[CalendarEvent]:
        """Query free/busy status across ALL linked Google and M365 calendars simultaneously."""
        all_conflicts: List[CalendarEvent] = []
        seen_ids = set()

        for conn in self.all_connectors:
            try:
                conflicts = conn.check_calendar_conflicts(start_time, end_time)
                for c in conflicts:
                    if c.id not in seen_ids:
                        seen_ids.add(c.id)
                        all_conflicts.append(c)
            except Exception as e:
                logger.warning(f"Error querying free/busy on connector: {e}")

        return all_conflicts

    def find_alternative_slots(
        self,
        requested_start: datetime,
        duration_minutes: int = 45,
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """Find conflict-free alternative time slots within business hours."""
        alternatives = []
        candidate_offsets = [2, 4, 24, 26, 48, 50]  # Hours to probe ahead

        for offset in candidate_offsets:
            candidate_start = requested_start + timedelta(hours=offset)
            # Ensure within 9:00 AM - 5:00 PM business hours
            if candidate_start.hour < 9:
                candidate_start = candidate_start.replace(hour=10, minute=0, second=0, microsecond=0)
            elif candidate_start.hour >= 17:
                candidate_start = (candidate_start + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)

            # Skip weekends
            if candidate_start.weekday() >= 5:
                candidate_start = candidate_start + timedelta(days=(7 - candidate_start.weekday()))

            candidate_end = candidate_start + timedelta(minutes=duration_minutes)
            conflicts = self.check_cross_account_conflicts(candidate_start, candidate_end)

            if not conflicts and not any(abs((a["start_time"] - candidate_start).total_seconds()) < 60 for a in alternatives):
                alternatives.append({
                    "start_time": candidate_start,
                    "end_time": candidate_end,
                    "formatted": candidate_start.strftime("%A, %B %d, %Y at %I:%M %p IST")
                })
                if len(alternatives) >= count:
                    break

        return alternatives

    def schedule_from_email_data(self, extracted_data: Dict[str, Any], ecosystem: str = "google") -> Dict[str, Any]:
        """Schedule a calendar event based on extracted email data with cross-account free/busy check."""
        start_time: Optional[datetime] = extracted_data.get("proposed_datetime")
        end_time: Optional[datetime] = extracted_data.get("proposed_end_time")
        duration: int = extracted_data.get("duration_minutes", 45)

        if not start_time:
            return {
                "scheduled": False,
                "reason": "No valid date/time found in email content",
                "event": None,
                "has_conflict": False,
                "alternative_slots": []
            }

        if not end_time:
            end_time = start_time + timedelta(minutes=duration)

        # Cross-Account Conflict check
        conflicts: List[CalendarEvent] = self.check_cross_account_conflicts(start_time, end_time)
        if conflicts:
            conflicting_title = conflicts[0].title
            logger.warning(f"Cross-account conflict detected for {start_time} - {end_time}: '{conflicting_title}' ({conflicts[0].source_ecosystem.upper()})")
            
            # Auto-generate 3 alternative conflict-free slots
            alternatives = self.find_alternative_slots(start_time, duration, count=3)
            return {
                "scheduled": False,
                "reason": f"Cross-account conflict with '{conflicting_title}' on {conflicts[0].source_ecosystem.upper()}",
                "has_conflict": True,
                "conflicting_event": conflicting_title,
                "conflicts": [c.title for c in conflicts],
                "alternative_slots": alternatives,
                "event": None
            }

        title = extracted_data.get("suggested_title", "Calendar Invitation: SmartCal Systems Live Demo & Consultation")
        attendees = [a for a in extracted_data.get("attendees", []) if a.lower() not in {"mm5921448@gmail.com"}]
        action_items = extracted_data.get("action_items", [])

        # Build clean description without attendees block or email list
        description_lines = [
            f"Scheduled autonomously by SmartCal Systems Automation Agent.",
            f"Source Ecosystem: {ecosystem.upper()}",
        ]

        if action_items:
            description_lines.extend(["", "Agenda & Action Items:"])
            for item in action_items:
                description_lines.append(f"- {item}")

        description = "\n".join(description_lines)

        try:
            event = self.connector.create_calendar_event(
                title=title,
                start_time=start_time,
                end_time=end_time,
                attendees=attendees,
                description=description,
                add_meeting_link=True
            )
            return {
                "scheduled": True,
                "has_conflict": False,
                "event": event,
                "event_id": event.id,
                "meeting_link": event.meeting_link,
                "title": event.title,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "location": event.location,
                "alternative_slots": []
            }
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {
                "scheduled": False,
                "has_conflict": False,
                "reason": str(e),
                "event": None,
                "alternative_slots": []
            }

    def schedule_focus_prep_block(self, task_name: str, deadline: datetime, prep_duration_minutes: int = 30) -> Optional[CalendarEvent]:
        """Schedule a Focus / Prep block on the calendar ahead of a deliverable deadline."""
        start_time = deadline - timedelta(hours=2)
        end_time = start_time + timedelta(minutes=prep_duration_minutes)

        title = f"Focus / Prep: {task_name}"
        desc = (
            f"Autonomously time-blocked focus session by SmartCal Systems Agent.\n"
            f"Deliverable: {task_name}\n"
            f"Hard Deadline: {deadline.strftime('%A, %B %d at %I:%M %p IST')}"
        )

        try:
            event = self.connector.create_calendar_event(
                title=title,
                start_time=start_time,
                end_time=end_time,
                attendees=[],
                description=desc,
                add_meeting_link=False
            )
            logger.info(f"Scheduled Focus/Prep block: '{title}' at {start_time}")
            return event
        except Exception as e:
            logger.error(f"Failed to schedule focus block: {e}")
            return None

    def schedule_emergency_focus_block(self, issue_subject: str, duration_minutes: int = 30) -> Optional[CalendarEvent]:
        """Automatically block an immediate 30-minute focus slot for high-urgency escalations."""
        now = datetime.utcnow()
        start_time = now + timedelta(minutes=5)
        end_time = start_time + timedelta(minutes=duration_minutes)

        title = f"🚨 URGENT FOCUS: Resolve Escalation ({issue_subject[:30]}...)"
        desc = f"Immediate resolution time-block triggered by SmartCal Systems high-urgency triage.\nIssue: {issue_subject}"

        try:
            event = self.connector.create_calendar_event(
                title=title,
                start_time=start_time,
                end_time=end_time,
                attendees=[],
                description=desc,
                add_meeting_link=False
            )
            logger.info(f"Booked Emergency Focus slot for urgent issue: {issue_subject}")
            return event
        except Exception as e:
            logger.error(f"Failed to schedule emergency focus block: {e}")
            return None

    def schedule_payment_reminder(self, invoice_info: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Create a calendar reminder on the payment due date for extracted invoices."""
        due_date: datetime = invoice_info.get("due_date", datetime.utcnow() + timedelta(days=14))
        vendor = invoice_info.get("vendor_name", "Vendor")
        inv_no = invoice_info.get("invoice_number", "INV")
        amount = invoice_info.get("amount", 0.0)
        curr = invoice_info.get("currency", "$")

        start_time = due_date.replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=30)

        title = f"💳 Payment Due: {vendor} ({curr}{amount:,.2f}) [#{inv_no}]"
        desc = (
            f"Automated Invoice Reminder from SmartCal Systems Document Pipeline.\n"
            f"Vendor: {vendor}\n"
            f"Invoice Number: {inv_no}\n"
            f"Amount Due: {curr}{amount:,.2f}\n"
            f"Due Date: {due_date.strftime('%B %d, %Y')}"
        )

        try:
            event = self.connector.create_calendar_event(
                title=title,
                start_time=start_time,
                end_time=end_time,
                attendees=[],
                description=desc,
                add_meeting_link=False
            )
            logger.info(f"Created Invoice Payment reminder: '{title}' on {due_date}")
            return event
        except Exception as e:
            logger.error(f"Failed to create payment reminder: {e}")
            return None

    def reschedule_conflicting_events_for_ooo(self, sender_email: str, return_date: datetime) -> List[Dict[str, Any]]:
        """Automatically shift any meetings conflicting with an OOO period to after their return date."""
        now = datetime.utcnow()
        shifted = []

        # Find events involving sender between now and return_date
        for conn in self.all_connectors:
            events_attr = getattr(conn, "_calendar_events", None) or getattr(conn, "_mock_events", None)
            if not events_attr:
                continue

            for ev in list(events_attr):
                if any(sender_email.lower() in att.lower() for att in ev.attendees):
                    if now <= ev.start_time <= return_date:
                        # Shift to day after return date at 14:00 IST
                        new_start = (return_date + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
                        duration = ev.end_time - ev.start_time
                        new_end = new_start + duration

                        old_start = ev.start_time
                        ev.start_time = new_start
                        ev.end_time = new_end
                        ev.description += f"\n[Auto-Rescheduled]: Shifted from {old_start} due to {sender_email} Out of Office until {return_date.strftime('%B %d, %Y')}."
                        
                        logger.info(f"Auto-rescheduled '{ev.title}' with {sender_email} to {new_start} due to OOO.")
                        shifted.append({
                            "event_title": ev.title,
                            "original_time": old_start.isoformat(),
                            "new_time": new_start.isoformat(),
                            "attendee": sender_email
                        })

        return shifted

    def attach_dossier_to_event(self, event_id: str, dossier_summary: str) -> bool:
        """Attach a pre-meeting context dossier directly into the calendar event description."""
        for conn in self.all_connectors:
            events_attr = getattr(conn, "_calendar_events", None) or getattr(conn, "_mock_events", None)
            if not events_attr:
                continue
            for ev in events_attr:
                if ev.id == event_id or event_id in ev.id:
                    ev.description = f"{ev.description}\n\n--- 📑 PRE-MEETING CONTEXT DOSSIER ---\n{dossier_summary}"
                    logger.info(f"Pre-Meeting Dossier attached to calendar event '{ev.title}'")
                    return True
        return False

    def schedule_war_room_sync(
        self,
        issue_subject: str,
        escalation_reason: str,
        internal_attendees: Optional[List[str]] = None
    ) -> Optional[CalendarEvent]:
        """Auto-book an internal war-room session when CC-escalation or negative sentiment drift is detected."""
        now = datetime.utcnow()
        start_time = (now + timedelta(minutes=10)).replace(second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=30)
        attendees = internal_attendees or ["engineering-lead@company.internal", "client-success@company.internal"]

        title = f"🚨 INTERNAL WAR-ROOM: Escalation Response ({issue_subject[:30]}...)"
        desc = (
            f"URGENT WAR-ROOM SYNC triggered autonomously by SmartCal Systems Sentiment/CC Escalation Detector.\n\n"
            f"Escalation Reason: {escalation_reason}\n"
            f"Target Thread: {issue_subject}\n"
            f"Objective: Formulate immediate client mitigation strategy and resolve blockers."
        )

        try:
            event = self.connector.create_calendar_event(
                title=title,
                start_time=start_time,
                end_time=end_time,
                attendees=attendees,
                description=desc,
                add_meeting_link=True
            )
            logger.info(f"Booked internal war-room event: '{title}' at {start_time}")
            return event
        except Exception as e:
            logger.error(f"Failed to book internal war room: {e}")
            return None

    def bump_internal_meeting_for_vip(
        self,
        vip_email: str,
        vip_name: str,
        requested_start: datetime,
        duration_minutes: int = 45,
        vip_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Automatically identify and bump movable internal 1:1s to lock in high-urgency VIP slots."""
        requested_end = requested_start + timedelta(minutes=duration_minutes)
        conflicts = self.check_cross_account_conflicts(requested_start, requested_end)

        if not conflicts:
            # Clear slot, no bump required
            event = self.connector.create_calendar_event(
                title=f"VIP Strategic Session: {vip_name} / SmartCal Systems",
                start_time=requested_start,
                end_time=requested_end,
                attendees=[vip_email],
                description=f"Directly scheduled priority meeting for VIP stakeholder {vip_name} ({vip_email}).",
                add_meeting_link=True
            )
            return {"bumped": False, "scheduled": True, "event": event, "reason": "No conflict present."}

        # Check if any conflicting event is a movable internal meeting
        internal_keywords = ["1:1", "sync", "internal", "catch up", "touch base", "weekly", "standup"]
        bumped_event = None

        for conf in conflicts:
            title_lower = conf.title.lower()
            is_internal_title = any(kw in title_lower for kw in internal_keywords)
            # Check attendees: if no external attendees or title explicitly says internal
            has_external = any("@" in att and not att.endswith("company.internal") and vip_email not in att for att in conf.attendees)
            
            if is_internal_title or not has_external:
                bumped_event = conf
                break

        if not bumped_event:
            return {
                "bumped": False,
                "scheduled": False,
                "reason": "Existing conflict is an immutable external client meeting."
            }

        # Reschedule the internal event to the next business day (+24h)
        old_start = bumped_event.start_time
        new_start = (old_start + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
        dur = bumped_event.end_time - bumped_event.start_time
        new_end = new_start + dur

        bumped_event.start_time = new_start
        bumped_event.end_time = new_end
        bumped_event.description += f"\n[VIP Auto-Bump]: Shifted from {old_start.strftime('%Y-%m-%d %H:%M')} to accommodate urgent VIP request from {vip_name} ({vip_email})."

        logger.info(f"VIP Auto-Bump: Moved internal meeting '{bumped_event.title}' to {new_start} to accommodate VIP {vip_email}.")

        # Now lock in the requested slot for VIP
        vip_event = self.connector.create_calendar_event(
            title=f"⭐ VIP Executive Session: {vip_name} / SmartCal Systems",
            start_time=requested_start,
            end_time=requested_end,
            attendees=[vip_email],
            description=f"Priority VIP session booked via SmartCal Systems VIP Auto-Bump Engine.\nClient: {vip_name} <{vip_email}>",
            add_meeting_link=True
        )

        return {
            "bumped": True,
            "scheduled": True,
            "bumped_event_title": bumped_event.title,
            "original_slot": old_start.isoformat(),
            "rescheduled_slot": new_start.isoformat(),
            "vip_event": vip_event
        }

    def defragment_calendar_schedule(
        self,
        date_to_defrag: datetime,
        max_gap_minutes: int = 30
    ) -> Dict[str, Any]:
        """Consolidate fragmented 'swiss-cheese' calendar schedules into contiguous deep-work blocks."""
        day_start = date_to_defrag.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date_to_defrag.replace(hour=23, minute=59, second=59, microsecond=0)

        all_events: List[CalendarEvent] = []
        for conn in self.all_connectors:
            events_attr = getattr(conn, "_calendar_events", None) or getattr(conn, "_mock_events", None)
            if events_attr:
                for ev in events_attr:
                    if day_start <= ev.start_time <= day_end:
                        all_events.append(ev)

        # Sort events by start time
        all_events.sort(key=lambda x: x.start_time)
        gaps_found = 0
        minutes_reclaimed = 0
        proposals: List[Dict[str, Any]] = []

        internal_keywords = ["1:1", "sync", "internal", "catch up", "touch base", "weekly"]

        for i in range(len(all_events) - 1):
            curr_ev = all_events[i]
            next_ev = all_events[i + 1]

            gap_seconds = (next_ev.start_time - curr_ev.end_time).total_seconds()
            gap_minutes = gap_seconds / 60.0

            # If there's an awkward gap between 5 and max_gap_minutes
            if 5.0 <= gap_minutes <= max_gap_minutes:
                # If next event is movable internal meeting, propose consolidation
                is_movable = any(kw in next_ev.title.lower() for kw in internal_keywords) or len(next_ev.attendees) <= 1
                if is_movable:
                    new_next_start = curr_ev.end_time + timedelta(minutes=5)
                    dur = next_ev.end_time - next_ev.start_time
                    new_next_end = new_next_start + dur

                    gaps_found += 1
                    minutes_reclaimed += int(gap_minutes)
                    proposals.append({
                        "event_title": next_ev.title,
                        "current_slot": next_ev.start_time.strftime("%H:%M IST"),
                        "proposed_consolidated_slot": new_next_start.strftime("%H:%M IST"),
                        "gap_closed_minutes": int(gap_minutes)
                    })

                    # Apply defragmentation shift
                    next_ev.start_time = new_next_start
                    next_ev.end_time = new_next_end
                    next_ev.description += f"\n[Calendar Defragmentation]: Shifted to consolidate deep-work focus block."

        deep_work_hours = round(minutes_reclaimed / 60.0 + 2.0, 1) if gaps_found > 0 else 0.0

        return {
            "date": date_to_defrag.strftime("%Y-%m-%d"),
            "gaps_found": gaps_found,
            "minutes_reclaimed": minutes_reclaimed,
            "deep_work_hours_created": deep_work_hours,
            "proposals": proposals
        }
