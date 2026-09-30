"""NLP Parser & Advanced Entity Extraction Engine for Email & Calendar Automation.

Extracts action items, proposed meeting slots with timezone negotiation,
deliverable commitments for time-blocking, OOO return dates, and invoice metadata.
"""
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import dateutil.parser
import pytz

COMMON_TZ_OFFSETS = {
    "UTC": 0, "GMT": 0,
    "EST": -5, "EDT": -4,
    "CST": -6, "CDT": -5,
    "MST": -7, "MDT": -6,
    "PST": -8, "PDT": -7,
    "IST": 5.5,  # Indian Standard Time (+05:30)
    "BST": 1, "CET": 1, "CEST": 2,
    "JST": 9, "AEST": 10
}


class EmailEntityExtractor:
    """Extracts structured entities, action items, dates, timezones, deliverables, OOO, and invoices."""

    def __init__(self, default_tz: str = "IST"):
        tz_name = "Asia/Kolkata" if default_tz == "IST" else default_tz
        try:
            self.default_tz = pytz.timezone(tz_name)
        except Exception:
            self.default_tz = pytz.timezone("Asia/Kolkata")

    def detect_compliance_intent(self, subject: str, body_text: str) -> Optional[str]:
        """Detect compliance commands: STOP / UNSUBSCRIBE / REVOKE / DELETE or I AGREE."""
        combined = f"{subject}\n{body_text}".lower()
        # Kill-switch: STOP, UNSUBSCRIBE, REVOKE, DELETE
        if re.search(r"\b(stop|unsubscribe|revoke|delete)\b", combined):
            return "revoke_and_delete"
        # Explicit Consent: "I AGREE", "AGREE", "ACCEPT TERMS", "I CONSENT"
        if re.search(r"\b(i\s+agree|agree|accept\s+terms|i\s+consent)\b", combined):
            return "consent_agree"
        return None

    def detect_plan_selection(self, subject: str, body_text: str) -> Optional[str]:
        """Detect when an incoming email contains 'plan 1', 'plan 2', or 'plan 3'."""
        combined = f"{subject}\n{body_text}".lower()
        if re.search(r"\bplan[\s\-_#]*1\b", combined):
            return "plan_1"
        if re.search(r"\bplan[\s\-_#]*2\b", combined):
            return "plan_2"
        if re.search(r"\bplan[\s\-_#]*3\b", combined):
            return "plan_3"
        return None

    def extract_all(
        self,
        subject: str,
        body_text: str,
        sender_name: str,
        sender_email: str,
        prior_attendees: Optional[List[str]] = None,
        role_routing_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run comprehensive entity extraction pipeline with sentiment drift and CC-escalation detection."""
        # Detect compliance intent (DPDP Act Kill-Switch vs Explicit Consent)
        compliance_intent = self.detect_compliance_intent(subject, body_text)

        # Detect plan replies (Plan 1, Plan 2, Plan 3)
        selected_plan = self.detect_plan_selection(subject, body_text)

        action_items = self.extract_action_items(body_text)
        proposed_slots = self.parse_proposed_times(body_text, subject)
        primary_slot = proposed_slots[0] if proposed_slots else {
            "start_time": None, "end_time": None, "duration_minutes": 45, "raw_text": "", "timezone_detected": "IST"
        }
        
        attendees = self.extract_attendees(body_text, sender_email)
        meeting_intent = self.detect_meeting_intent(subject, body_text)
        deliverables = self.extract_deliverable_commitments(body_text)
        ooo_info = self.detect_out_of_office(subject, body_text)
        invoice_info = self.extract_invoice_metadata(subject, body_text)
        urgency = self.detect_urgency(subject, body_text, is_ooo=ooo_info["is_ooo"])

        # Sentiment drift and CC escalation detection
        sentiment_info = self.detect_sentiment_drift(subject, body_text)
        cc_escalation = self.detect_cc_escalation(attendees, prior_attendees)
        role_intent = self.detect_role_intent(subject, body_text, role_routing_config)

        # Compliance intent & Plan selection take priority over general meeting scheduling
        is_meeting_req = meeting_intent["is_meeting"]
        if compliance_intent or selected_plan:
            is_meeting_req = False
            meeting_intent = {"is_meeting": False, "confidence": 0.0, "matched_keywords": []}

        # Bump urgency to high if sentiment drifts to frustrated or CC escalated
        if sentiment_info["is_negative"] or cc_escalation["is_cc_escalation"]:
            urgency = "high"

        # Classify email category
        email_type = self.detect_email_type(
            subject, body_text, is_meeting_req, action_items, ooo_info["is_ooo"], invoice_info["is_invoice"],
            selected_plan=selected_plan, compliance_intent=compliance_intent
        )

        suggested_title = self.generate_meeting_title(subject, meeting_intent, sender_name)

        return {
            "sender_name": sender_name,
            "sender_email": sender_email,
            "subject": subject,
            "action_items": action_items,
            "proposed_datetime": primary_slot["start_time"],
            "proposed_end_time": primary_slot["end_time"],
            "duration_minutes": primary_slot["duration_minutes"],
            "datetime_raw_match": primary_slot["raw_text"],
            "timezone_detected": primary_slot.get("timezone_detected", "IST"),
            "proposed_slots": proposed_slots,
            "attendees": attendees,
            "meeting_intent": meeting_intent,
            "is_meeting_request": is_meeting_req,
            "meeting_confidence": meeting_intent["confidence"],
            "selected_plan": selected_plan,
            "compliance_intent": compliance_intent,
            "urgency": urgency,
            "email_type": email_type,
            "deliverables": deliverables,
            "out_of_office": ooo_info,
            "invoice_metadata": invoice_info,
            "suggested_title": suggested_title,
            "sentiment": sentiment_info,
            "cc_escalation": cc_escalation,
            "role_intent": role_intent,
            "requires_war_room": sentiment_info["is_negative"] or cc_escalation["is_cc_escalation"]
        }

    def detect_email_type(
        self,
        subject: str,
        body_text: str,
        is_meeting: bool,
        action_items: List[str],
        is_ooo: bool = False,
        is_invoice: bool = False,
        selected_plan: Optional[str] = None,
        compliance_intent: Optional[str] = None
    ) -> str:
        """Classify email category to drive tailored response drafting."""
        if compliance_intent == "revoke_and_delete":
            return "compliance_revoke"
        if compliance_intent == "consent_agree":
            return "compliance_consent"
        if selected_plan:
            return "checkout"
        if is_ooo:
            return "out_of_office"
        if is_invoice:
            return "invoice"
        if is_meeting:
            return "meeting_request"
        combined = f"{subject} {body_text}".lower()
        if "?" in body_text or any(q in combined for q in ["how to", "could you explain", "status of", "inquiry", "clarification", "question"]):
            return "inquiry"
        if action_items:
            return "task_assignment"
        return "general_update"

    def parse_proposed_times(self, text: str, subject: str) -> List[Dict[str, Any]]:
        """Extract all proposed meeting slots with natural language and timezone support."""
        now = datetime.utcnow()
        duration_minutes = 45

        # Check duration
        dur_match = re.search(r"(\d+)\s*(?:-| )(?:minute|min)s?\b", text, re.IGNORECASE)
        if dur_match:
            duration_minutes = int(dur_match.group(1))
        else:
            hr_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-| )hour\b", text, re.IGNORECASE)
            if hr_match:
                duration_minutes = int(float(hr_match.group(1)) * 60)

        full_content = f"{subject}\n{text}"
        slots: List[Dict[str, Any]] = []

        # Detect Timezone in string (default to IST)
        tz_pattern = r"\b(IST|UTC|GMT|EST|EDT|PST|PDT|CST|CDT|MST|MDT|BST|CET|CEST|JST|AEST)\b"
        found_tz_match = re.search(tz_pattern, full_content)
        detected_tz = found_tz_match.group(1).upper() if found_tz_match else "IST"
        tz_offset_hours = COMMON_TZ_OFFSETS.get(detected_tz, 0)

        # Regex patterns covering relative days, weekdays, and explicit dates
        time_regexes = [
            r"([A-Za-z]+ \d{1,2},? \d{4}(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))?(?:\s+[A-Za-z]{2,4})?)",
            r"(\b(?:tomorrow|today)(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))?(?:\s+[A-Za-z]{2,4})?\b)",
            r"(\b(?:this|next)?\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))(?:\s+[A-Za-z]{2,4})?\b)",
            r"(\b(?:Monday|Tuesday|Wednesday|Thursday|Friday)\b(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))?(?:\s+[A-Za-z]{2,4})?\b)",
            r"(\d{4}-\d{2}-\d{2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)"
        ]

        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }

        for regex in time_regexes:
            for match in re.finditer(regex, full_content, re.IGNORECASE):
                raw_match = match.group(1).strip()
                try:
                    slot_dt = None
                    lowered = raw_match.lower()

                    # Extract time component if present
                    hour = 14
                    minute = 0
                    t_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)", raw_match)
                    if t_match:
                        h = int(t_match.group(1))
                        m = int(t_match.group(2) or 0)
                        ampm = t_match.group(3).upper()
                        if ampm == "PM" and h < 12:
                            h += 12
                        elif ampm == "AM" and h == 12:
                            h = 0
                        hour = h
                        minute = m

                    if "tomorrow" in lowered:
                        slot_dt = (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
                    elif "today" in lowered:
                        slot_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    elif any(w in lowered for w in weekday_map.keys()):
                        for w_name, w_idx in weekday_map.items():
                            if w_name in lowered:
                                days_ahead = (w_idx - now.weekday()) % 7
                                if days_ahead <= 0:
                                    days_ahead += 7
                                slot_dt = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
                                break
                    else:
                        # Clean explicit date
                        clean_dt_str = re.sub(r"\bat\b", " ", raw_match, flags=re.IGNORECASE)
                        clean_dt_str = re.sub(tz_pattern, "", clean_dt_str, flags=re.IGNORECASE).strip()
                        parsed = dateutil.parser.parse(clean_dt_str, fuzzy=True, default=now)
                        slot_dt = parsed

                    if slot_dt:
                        # Normalize to UTC using detected timezone offset
                        utc_dt = slot_dt - timedelta(hours=tz_offset_hours)
                        end_utc = utc_dt + timedelta(minutes=duration_minutes)

                        # Avoid duplicates
                        if not any(abs((s["start_time"] - utc_dt).total_seconds()) < 60 for s in slots):
                            slots.append({
                                "start_time": utc_dt,
                                "end_time": end_utc,
                                "duration_minutes": duration_minutes,
                                "raw_text": raw_match,
                                "timezone_detected": detected_tz
                            })
                except Exception:
                    continue

        if not slots and re.search(r"\b(meet|schedule|call|sync|session|discuss)\b", full_content, re.IGNORECASE):
            fallback_start = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
            slots.append({
                "start_time": fallback_start,
                "end_time": fallback_start + timedelta(minutes=duration_minutes),
                "duration_minutes": duration_minutes,
                "raw_text": "Next Business Day 2:00 PM IST",
                "timezone_detected": "IST"
            })

        return slots

    def extract_deliverable_commitments(self, text: str) -> List[Dict[str, Any]]:
        """Extract commitment deadlines for task time-blocking (e.g. 'I will share the deck by Friday EOD')."""
        commitments = []
        now = datetime.utcnow()
        lines = text.split("\n")

        pattern = re.compile(
            r"\b(i(?:\'ll| will)|we(?:\'ll| will)|please)?\s*(share|send|submit|deliver|complete|finalize|prepare)\s+([^.]+?)\s+(?:by|before|due on)\s+([A-Za-z0-9\s,:]+)",
            re.IGNORECASE
        )

        for line in lines:
            line_str = line.strip()
            m = pattern.search(line_str)
            if m:
                action_verb = m.group(2)
                task_item = f"{action_verb} {m.group(3).strip()}"
                raw_deadline = m.group(4).strip()

                deadline_dt = None
                try:
                    if "eod" in raw_deadline.lower() or "end of day" in raw_deadline.lower():
                        cleaned_dl = re.sub(r"\b(eod|end of day)\b", "", raw_deadline, flags=re.IGNORECASE).strip()
                        base_dt = dateutil.parser.parse(cleaned_dl, fuzzy=True, default=now) if cleaned_dl else now
                        deadline_dt = base_dt.replace(hour=18, minute=0, second=0, microsecond=0)
                    else:
                        deadline_dt = dateutil.parser.parse(raw_deadline, fuzzy=True, default=now)
                except Exception:
                    deadline_dt = (now + timedelta(days=2)).replace(hour=17, minute=0, second=0, microsecond=0)

                commitments.append({
                    "task": task_item.capitalize(),
                    "deadline": deadline_dt,
                    "raw_deadline": raw_deadline,
                    "prep_duration_minutes": 30
                })

        return commitments

    def detect_out_of_office(self, subject: str, body_text: str) -> Dict[str, Any]:
        """Detect Out of Office auto-replies and extract sender's return date."""
        combined = f"{subject}\n{body_text}".lower()
        is_ooo = any(k in combined for k in [
            "out of office", "ooo", "auto-reply", "away from my desk", 
            "annual leave", "maternity leave", "paternity leave", "back in the office"
        ])

        return_date = None
        raw_return_date = ""

        if is_ooo:
            now = datetime.utcnow()
            date_matches = re.findall(
                r"(?:back|return(?:ing)?|available)\s+(?:on|by|after)?\s*([A-Za-z]+ \d{1,2}(?:,? \d{4})?|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
                body_text,
                re.IGNORECASE
            )
            if date_matches:
                raw_return_date = date_matches[0]
                try:
                    return_date = dateutil.parser.parse(raw_return_date, fuzzy=True, default=now)
                    if return_date < now:
                        return_date = return_date.replace(year=now.year + 1)
                except Exception:
                    return_date = now + timedelta(days=7)
            else:
                return_date = now + timedelta(days=5)
                raw_return_date = "In 5 Days"

        return {
            "is_ooo": is_ooo,
            "return_date": return_date,
            "raw_return_date": raw_return_date
        }

    def extract_invoice_metadata(self, subject: str, body_text: str) -> Dict[str, Any]:
        """Extract invoice and contract metadata for financial calendar reminders."""
        combined = f"{subject}\n{body_text}"
        is_invoice = bool(re.search(r"\b(invoice|bill|payment due|contract|agreement|renewal|receipt)\b", combined, re.IGNORECASE))

        if not is_invoice:
            return {"is_invoice": False}

        now = datetime.utcnow()
        # Extract invoice number: prioritize #NUMBER or identifiers with digits
        inv_match = re.search(r"#\s*([A-Za-z0-9\-_]+)", combined)
        if not inv_match:
            inv_match = re.search(r"\b(?:invoice|inv|bill)\s*(?:no\.?|num(?:ber)?)?\s*[:#]?\s*([A-Za-z0-9\-_]*\d[A-Za-z0-9\-_]*)", combined, re.IGNORECASE)

        inv_number = inv_match.group(1).strip() if inv_match else "INV-AUTO"

        # Extract amount
        amt_match = re.search(r"(\$|€|£|INR|USD)\s*([0-9,]+(?:\.[0-9]{2})?)", combined, re.IGNORECASE)
        amount = 0.0
        currency = "$"
        if amt_match:
            currency = amt_match.group(1)
            amount = float(amt_match.group(2).replace(",", ""))

        # Extract due date
        due_match = re.search(r"(?:due|payment due|by)\s*(?:date|on|before)?\s*([A-Za-z]+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})", combined, re.IGNORECASE)
        due_date = now + timedelta(days=14)
        raw_due_date = "Net 14 Days"
        if due_match:
            raw_due_date = due_match.group(1)
            try:
                due_date = dateutil.parser.parse(raw_due_date, fuzzy=True, default=now)
            except Exception:
                pass

        # Vendor / sender extraction (stop at line break)
        vendor_match = re.search(r"(?:from|vendor|company):\s*([^\n\r,]+)", combined, re.IGNORECASE)
        vendor_name = vendor_match.group(1).strip() if vendor_match else "Vendor"

        return {
            "is_invoice": True,
            "invoice_number": inv_number,
            "vendor_name": vendor_name,
            "amount": amount,
            "currency": currency,
            "due_date": due_date,
            "raw_due_date": raw_due_date
        }

    def extract_action_items(self, text: str) -> List[str]:
        """Extract bulleted or numbered action items and directive sentences."""
        items: List[str] = []
        lines = text.split("\n")
        in_action_section = False

        bullet_pattern = re.compile(r"^\s*([-*•]|\d+[\).])\s+(.+)$")
        action_verbs = r"(review|finalize|confirm|address|validate|send|prepare|check|schedule|update|investigate|deploy|fix)"
        action_sentence_pattern = re.compile(rf"^(please\s+)?{action_verbs}\b", re.IGNORECASE)

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Header detection
            if re.search(r"\b(action items?|agenda|next steps|todo|tasks?)\b", line_str, re.IGNORECASE):
                in_action_section = True
                continue

            m = bullet_pattern.match(line_str)
            if m:
                items.append(m.group(2).strip())
                continue

            if in_action_section and len(line_str) > 10:
                if line_str.startswith(("Best regards", "Thanks", "Sincerely", "Regards")):
                    in_action_section = False
                else:
                    items.append(line_str)
            elif action_sentence_pattern.match(line_str) and len(line_str) > 15:
                items.append(line_str)

        return list(dict.fromkeys(items))[:8]

    def extract_attendees(self, text: str, sender_email: str) -> List[str]:
        """Extract email addresses mentioned in body and add sender, strictly filtering personal addresses."""
        blocked_personal = {"mm5921448@gmail.com"}
        emails = set()
        if sender_email and sender_email.lower() not in blocked_personal:
            emails.add(sender_email.lower())

        found = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        for e in found:
            if e.lower() not in blocked_personal:
                emails.add(e.lower())

        return sorted(list(emails))

    def detect_meeting_intent(self, subject: str, body_text: str) -> Dict[str, Any]:
        """Detect if email is proposing or requesting a meeting with confidence score."""
        combined = f"{subject} {body_text}".lower()
        meeting_patterns = [
            r"\bmeet\b", r"\bmeeting\b", r"\bcall\b", r"\bsync\b", r"\bdemo\b",
            r"\bcalendar\b", r"\binvite\b", r"\bappointment\b", r"\bcatch up\b",
            r"\btouch base\b", r"\bdiscussion\b", r"\bworking session\b", r"\bschedule\b"
        ]
        matched = [p for p in meeting_patterns if re.search(p, combined)]
        score = len(matched)
        confidence = min(1.0, score * 0.35)
        return {
            "is_meeting": score >= 1,
            "confidence": round(confidence, 2),
            "matched_keywords": matched
        }

    def detect_urgency(self, subject: str, body_text: str, is_ooo: bool = False) -> str:
        """Classify urgency level: low, normal, high."""
        if is_ooo:
            return "normal"
        # Ignore boilerplate auto-reply disclaimers like 'for urgent inquiries/queries please contact...'
        cleaned_body = re.sub(
            r"\bfor\s+(?:urgent|immediate)\s+(?:queries|inquiries|matters|assistance|issues)\b.*?(?:\.|\n|$)",
            "",
            body_text,
            flags=re.IGNORECASE
        )
        combined = f"{subject} {cleaned_body}".lower()
        if any(w in combined for w in ["urgent", "asap", "immediate", "critical", "emergency"]):
            return "high"
        if any(w in combined for w in ["important", "priority", "deadline", "review required"]):
            return "medium"
        return "normal"

    def generate_meeting_title(self, subject: str, intent: Dict[str, Any], sender_name: str) -> str:
        """Create a clean, professional calendar title strictly using the standard format."""
        return "Calendar Invitation: SmartCal Systems Live Demo & Consultation"

    def extract_mom_and_action_owners(self, transcript_text: str) -> Dict[str, Any]:
        """Extract Minutes of Meeting (MoM), key decisions, and action items with owners from meeting transcripts."""
        lines = [line.strip() for line in transcript_text.split("\n") if line.strip()]
        decisions: List[str] = []
        action_items: List[Dict[str, str]] = []
        topics: List[str] = []

        decision_pattern = re.compile(
            r"\b(?:decided|decision|agreed|resolution|approved|concluded)\s*(?:to|that|:)?\s*(.+)", 
            re.IGNORECASE
        )
        
        owner_action_pattern = re.compile(
            r"(?:([A-Za-z]+)\s*(?:\([^)]+\))?:\s*)?(?:action\s*item\s*:?\s*)?([A-Za-z]+)?\s*(?:will|to|shall)\s+([^.]+?)(?:\s+(?:by|before|on)\s+([A-Za-z0-9\s,:]+))?(?:\.|$)",
            re.IGNORECASE
        )

        for line in lines:
            dec_m = decision_pattern.search(line)
            if dec_m:
                decisions.append(dec_m.group(1).strip().capitalize())

            if any(k in line.lower() for k in ["action item", "will deliver", "will complete", "will send", "will coordinate", "will review", "to deliver", "to finalize"]):
                act_m = owner_action_pattern.search(line)
                if act_m:
                    speaker = act_m.group(1) or ""
                    named_owner = act_m.group(2) or ""
                    task = act_m.group(3).strip() if act_m.group(3) else line
                    deadline = act_m.group(4).strip() if act_m.group(4) else "TBD"

                    owner = named_owner if named_owner and named_owner.lower() not in ["i", "we", "action"] else (speaker or "Team")
                    action_items.append({
                        "owner": owner.capitalize(),
                        "task": task.capitalize(),
                        "deadline": deadline
                    })
                else:
                    action_items.append({
                        "owner": "Team",
                        "task": line.capitalize(),
                        "deadline": "TBD"
                    })

            if any(k in line.lower() for k in ["agenda", "reviewing", "discussing", "milestones", "architecture", "security", "deliverables"]):
                topics.append(line[:80])

        if not decisions:
            decisions.append("Aligned on cross-functional rollout schedule and technical benchmarks.")

        summary_preview = (
            f"Concluded sync with {len(lines)} recorded dialogue turns. "
            f"Extracted {len(decisions)} key decisions and {len(action_items)} action items."
        )

        return {
            "summary": summary_preview,
            "decisions": list(dict.fromkeys(decisions))[:5],
            "action_items": action_items[:8],
            "key_topics": list(dict.fromkeys(topics))[:4]
        }

    def detect_sentiment_drift(self, subject: str, body_text: str) -> Dict[str, Any]:
        """Detect negative or frustrated sentiment indicating thread escalation."""
        combined = f"{subject} {body_text}".lower()
        frustration_keywords = [
            "unacceptable", "disappointed", "frustrated", "escalat", "breach", 
            "delay", "delays", "failed to deliver", "unresolved", "immediate escalation",
            "legal counsel", "poor service", "not working", "still broken", "losing patience",
            "unhappy", "ridiculous", "severely impacted"
        ]
        matched = [k for k in frustration_keywords if k in combined]
        is_negative = len(matched) >= 1
        return {
            "is_negative": is_negative,
            "sentiment": "frustrated" if is_negative else "neutral",
            "frustration_score": min(1.0, len(matched) * 0.4),
            "matched_signals": matched
        }

    def detect_cc_escalation(self, current_attendees: List[str], prior_attendees: Optional[List[str]] = None) -> Dict[str, Any]:
        """Detect when new senior stakeholders or escalated parties are added to CC."""
        if not prior_attendees:
            return {"is_cc_escalation": False, "new_attendees": [], "senior_stakeholders_added": []}

        prior_set = {a.lower() for a in prior_attendees}
        new_attendees = [a for a in current_attendees if a.lower() not in prior_set]

        senior_markers = ["vp", "director", "head", "chief", "exec", "legal", "c-level", "lead", "counsel"]
        senior_added = [a for a in new_attendees if any(m in a.lower() for m in senior_markers)]

        is_escalation = len(senior_added) > 0 or len(new_attendees) >= 2
        return {
            "is_cc_escalation": is_escalation,
            "new_attendees": new_attendees,
            "senior_stakeholders_added": senior_added
        }

    def detect_role_intent(self, subject: str, body_text: str, role_routing_config: Optional[Dict[str, Any]] = None) -> str:
        """Classify query into operational vs executive intent for role-based cross-inbox handoff."""
        combined = f"{subject} {body_text}".lower()
        cfg = role_routing_config or {}
        ops_kw = cfg.get("operations_keywords", [
            "support", "bug", "ticket", "invoice", "billing", "access", 
            "operational", "technical issue", "error", "incident", "dns", "provisioning"
        ])
        exec_kw = cfg.get("executive_keywords", [
            "strategy", "board", "investor", "partnership", "confidential", "m&a", "advisory"
        ])

        if any(w in combined for w in ops_kw):
            return "operations"
        if any(w in combined for w in exec_kw):
            return "executive"
        return "general"
