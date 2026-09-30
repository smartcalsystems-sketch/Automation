"""Workflow Orchestrator for Multi-Account Autonomous Email & Calendar Automation Agent.

Implements all 4 advanced pillars:
1. Cross-Account Free/Busy Sync & Natural Language Slot Negotiation
2. Real-Time High-Urgency Escalation Webhook & Emergency Focus Blocking
3. Automated 48-Hour No-Reply Chasers & Task/Deadline Time-Blocking
4. Invoice / Contract Extraction & OOO Auto-Rescheduling
5. Pre-Meeting Context Dossiers & Confidence-Based Approval Routing
"""
import logging
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from config.settings import load_settings, save_settings
from auth.vault import CredentialVault
from auth.rdp_session import RDPSessionManager
from connectors.base_connector import BaseEcosystemConnector, EmailMessage, CalendarEvent
from connectors.google_connector import GoogleWorkspaceConnector, is_system_or_noreply
from connectors.m365_connector import Microsoft365Connector
from connectors.mock_connector import MockEcosystemConnector
from engine.nlp_parser import EmailEntityExtractor
from engine.email_drafter import ContextualEmailDrafter
from engine.calendar_scheduler import UnifiedCalendarScheduler
from pipeline.audit_logger import AuditLogger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AutomationAgent.Pipeline")


class AutomationWorkflowManager:
    """Master workflow manager controlling multi-account Google Workspace and Microsoft 365 automations."""

    def __init__(self, force_simulation: bool = False):
        self.settings = load_settings()
        self.vault = CredentialVault()
        self.audit_logger = AuditLogger()
        self.force_simulation = force_simulation
        self.extractor = EmailEntityExtractor(default_tz=self.settings.get("default_timezone", "IST"))
        self.rdp_manager = RDPSessionManager(self.settings.get("rdp", {}))
        
        # Registry of active account connectors: { account_id: { "meta": ..., "connector": ... } }
        self.account_connectors: Dict[str, Dict[str, Any]] = {}
        self._initialize_connectors()

    def _initialize_connectors(self) -> None:
        """Initialize connectors for all configured and enabled accounts."""
        self.account_connectors.clear()
        configured_accounts = self.vault.list_accounts(enabled_only=True)

        if not self.force_simulation and configured_accounts:
            for acc in configured_accounts:
                acc_id = acc.get("id")
                eco = acc.get("ecosystem", "google")
                label = acc.get("label", acc.get("email", acc_id))

                if eco == "google" and acc.get("email") and acc.get("app_password"):
                    logger.info(f"Initializing Live Google Workspace connector for account: {label} ({acc['email']})")
                    connector = GoogleWorkspaceConnector(acc, self.settings)
                elif eco == "m365" and acc.get("email") and acc.get("password"):
                    logger.info(f"Initializing Live Microsoft 365 connector for account: {label} ({acc['email']})")
                    connector = Microsoft365Connector(acc, self.settings)
                else:
                    logger.warning(f"Account {label} missing required credentials. Skipping live init.")
                    continue

                self.account_connectors[acc_id] = {
                    "meta": acc,
                    "connector": connector
                }

        # If no live accounts are configured or simulation requested, initialize multi-account simulation sandboxes
        if not self.account_connectors or self.force_simulation:
            logger.info("Initializing Multi-Account Sandbox Connectors (Google + M365)...")
            sim_accounts = [
                {
                    "id": "sim_google_work",
                    "label": "Primary Google Workspace (Work)",
                    "ecosystem": "google",
                    "email": "sarah.jenkins@acmepartners.com",
                    "enabled": True,
                    "auto_send_drafts": True,
                    "display_name": "SmartCal Systems Assistant"
                },
                {
                    "id": "sim_m365_enterprise",
                    "label": "Corporate Microsoft 365 (Enterprise)",
                    "ecosystem": "m365",
                    "email": "dchen@enterprise365.net",
                    "enabled": True,
                    "auto_send_drafts": True,
                    "display_name": "SmartCal Systems Scheduling Agent"
                }
            ]
            for sim_acc in sim_accounts:
                self.account_connectors[sim_acc["id"]] = {
                    "meta": sim_acc,
                    "connector": MockEcosystemConnector(ecosystem=sim_acc["ecosystem"])
                }

    def _get_all_connectors(self) -> List[BaseEcosystemConnector]:
        """Return list of all active connector instances across all accounts for cross-account sync."""
        return [entry["connector"] for entry in self.account_connectors.values()]

    def run_health_check(self) -> Dict[str, Any]:
        """Perform diagnostics across all registered accounts."""
        results = {}
        for acc_id, entry in self.account_connectors.items():
            meta = entry["meta"]
            connector: BaseEcosystemConnector = entry["connector"]
            conn_res = connector.test_connection()
            results[acc_id] = {
                "label": meta.get("label", acc_id),
                "ecosystem": meta.get("ecosystem"),
                "email": meta.get("email"),
                "success": conn_res.get("success", False),
                "message": conn_res.get("message", "")
            }

        if self.settings.get("auth_mode") == "rdp" or self.settings.get("rdp", {}).get("enabled"):
            results["rdp"] = {
                "label": "Remote Desktop Gateway",
                "ecosystem": "rdp",
                "email": "N/A",
                "success": self.rdp_manager.check_rdp_reachability(),
                "message": f"Host: {self.rdp_manager.host}:{self.rdp_manager.port}"
            }

        return results

    def process_all_ecosystems(self, target_account_id: Optional[str] = None) -> Dict[str, Any]:
        """Scan all accounts (or a targeted account) for unread emails and execute full workflow pipeline."""
        start_time = datetime.utcnow()
        summary = {
            "status": "completed",
            "start_time": start_time.isoformat(),
            "accounts_scanned": 0,
            "emails_scanned": 0,
            "emails_processed": 0,
            "drafts_created": 0,
            "events_scheduled": 0,
            "conflicts_detected": 0,
            "escalations_triggered": 0,
            "focus_blocks_scheduled": 0,
            "invoices_extracted": 0,
            "ooo_rescheduled": 0,
            "account_summaries": {},
            "items": []
        }

        trigger_mode = self.settings.get("trigger_mode", "all_unread")
        global_keywords = self.settings.get("keywords", []) if trigger_mode == "keywords" else None
        all_connectors = self._get_all_connectors()

        for acc_id, entry in self.account_connectors.items():
            if target_account_id and acc_id != target_account_id:
                continue

            meta = entry["meta"]
            connector: BaseEcosystemConnector = entry["connector"]
            label = meta.get("label", acc_id)
            eco_name = meta.get("ecosystem", "google")
            auto_send = meta.get("auto_send_drafts", self.settings.get("auto_send_drafts", False))
            display_name = meta.get("display_name", "SmartCal Systems Workflow Agent")
            
            # Circuit Breaker Check
            if connector.is_circuit_open():
                logger.warning(f"Account '{label}' circuit breaker is OPEN ({connector.circuit_reason}). Queue paused.")
                summary["account_summaries"][acc_id] = {
                    "label": label,
                    "scanned": 0,
                    "processed": 0,
                    "circuit_open": True,
                    "circuit_reason": connector.circuit_reason
                }
                continue

            drafter = ContextualEmailDrafter(sender_display_name=display_name)
            # Unified scheduler with cross-account free/busy synchronization
            scheduler = UnifiedCalendarScheduler(connector=connector, all_connectors=all_connectors)

            logger.info(f"Scanning unread emails for account '{label}' ({eco_name.upper()})...")
            unread_emails: List[EmailMessage] = connector.fetch_unread_emails(keywords=global_keywords)

            summary["accounts_scanned"] += 1
            summary["emails_scanned"] += len(unread_emails)
            acc_processed = 0

            for email_msg in unread_emails:
                item_result = self._process_single_email(
                    email_msg=email_msg,
                    connector=connector,
                    scheduler=scheduler,
                    drafter=drafter,
                    eco_name=eco_name,
                    account_meta=meta,
                    auto_send=auto_send
                )
                summary["items"].append(item_result)
                summary["emails_processed"] += 1
                acc_processed += 1
                if item_result.get("draft_created"):
                    summary["drafts_created"] += 1
                if item_result.get("event_scheduled"):
                    summary["events_scheduled"] += 1
                if item_result.get("has_conflict"):
                    summary["conflicts_detected"] += 1
                if item_result.get("escalation_triggered"):
                    summary["escalations_triggered"] += 1
                if item_result.get("focus_blocks_scheduled"):
                    summary["focus_blocks_scheduled"] += item_result["focus_blocks_scheduled"]
                if item_result.get("invoice_extracted"):
                    summary["invoices_extracted"] += 1
                if item_result.get("ooo_rescheduled"):
                    summary["ooo_rescheduled"] += 1

            summary["account_summaries"][acc_id] = {
                "label": label,
                "scanned": len(unread_emails),
                "processed": acc_processed
            }

        # Run daemon checks: follow-up chasers, pre-meeting dossiers, post-meeting MoMs, and no-show auto-recovery
        summary["followups_chased"] = self.check_and_stage_followup_chasers()
        summary["dossiers_attached"] = self.generate_pre_meeting_dossiers()
        summary["moms_dispatched"] = self.process_ended_meetings_and_dispatch_mom()
        summary["noshow_recoveries"] = self.check_live_meeting_attendance_and_recover()

        summary["end_time"] = datetime.utcnow().isoformat()
        return summary

    def _process_single_email(
        self,
        email_msg: EmailMessage,
        connector: BaseEcosystemConnector,
        scheduler: UnifiedCalendarScheduler,
        drafter: ContextualEmailDrafter,
        eco_name: str,
        account_meta: Dict[str, Any],
        auto_send: bool
    ) -> Dict[str, Any]:
        """Process an individual email across all 4 pillars."""
        acc_label = account_meta.get("label", email_msg.source_ecosystem)
        logger.info(f"[{acc_label}] Processing message '{email_msg.subject}' from {email_msg.sender_email}")

        # STRICT PRIVACY & OPT-OUT CHECK (config/unsubscribed.json)
        if self.vault.is_unsubscribed(email_msg.sender_email):
            logger.info(f"Skipping unsubscribed / opted-out sender: '{email_msg.sender_email}'")
            connector.mark_email_as_read(email_msg.id)
            return {
                "id": email_msg.id,
                "account_id": account_meta.get("id"),
                "account_label": acc_label,
                "ecosystem": eco_name,
                "sender": email_msg.sender_email,
                "subject": email_msg.subject,
                "skipped": True,
                "reason": "unsubscribed_user",
                "draft_created": False,
                "event_scheduled": False,
                "auto_sent": False
            }

        # STRICTLY BLOCK SYSTEM & NO-REPLY EMAILS
        if is_system_or_noreply(email_msg.sender_email, email_msg.subject):
            logger.info(f"Skipping system/no-reply email from '{email_msg.sender_email}' (Subject: '{email_msg.subject}')")
            connector.mark_email_as_read(email_msg.id)
            return {
                "id": email_msg.id,
                "account_id": account_meta.get("id"),
                "account_label": acc_label,
                "ecosystem": eco_name,
                "sender": email_msg.sender_email,
                "subject": email_msg.subject,
                "skipped": True,
                "reason": "system_or_noreply_blocked",
                "draft_created": False,
                "event_scheduled": False,
                "auto_sent": False
            }

        # Mark unread email as read IMMEDIATELY upon intake to prevent duplicate processing
        connector.mark_email_as_read(email_msg.id)

        # 1. NLP Entity Extraction
        prior_attendees = None
        if email_msg.thread_id:
            for r in self.audit_logger.get_recent_records(limit=30):
                if r.get("email_id") == email_msg.thread_id:
                    prior_attendees = r.get("attendees", [])
                    break

        extracted = self.extractor.extract_all(
            subject=email_msg.subject,
            body_text=email_msg.body_text,
            sender_name=email_msg.sender_name,
            sender_email=email_msg.sender_email,
            prior_attendees=prior_attendees,
            role_routing_config=self.settings.get("role_routing")
        )

        compliance_intent = extracted.get("compliance_intent")

        # 1a. INSTANT "STOP / REVOKE / DELETE" KILL-SWITCH (DPDP ACT 2023)
        if compliance_intent == "revoke_and_delete":
            logger.warning(f"INSTANT KILL-SWITCH TRIGGERED by '{email_msg.sender_email}' (Subject: '{email_msg.subject}')")
            
            # a) Immediately remove credentials from auth/vault.py (config/credentials.json)
            self.vault.delete_account_by_email(email_msg.sender_email)
            
            # b) Add their email to config/unsubscribed.json so they are never contacted again
            self.vault.add_to_unsubscribed(email_msg.sender_email)
            
            # c) Update config/consent_log.json with status: "REVOKED_AND_WIPED"
            self.vault.update_consent_status(email_msg.sender_email, status="REVOKED_AND_WIPED")
            
            # d) Send one final confirmation email:
            # "Your credentials and data have been permanently deleted from SmartCal Systems in compliance with the Indian DPDP Act, 2023."
            del_draft = drafter.generate_dpdp_deletion_email(original_subject=email_msg.subject)
            sent_ok = connector.send_email(
                recipient=email_msg.sender_email,
                subject=del_draft["subject"],
                body=del_draft["body"],
                reply_to_id=email_msg.thread_id or email_msg.id
            )
            
            # Log non-sensitive audit metadata (DPDP Zero Private Data Retention)
            self.audit_logger.log_workflow_execution({
                "account_id": account_meta.get("id"),
                "account_label": acc_label,
                "urgency": "high",
                "meeting_time": None,
                "event_scheduled": False,
                "has_conflict": False,
                "draft_created": True,
                "auto_sent": bool(sent_ok),
                "is_autonomous_approved": True,
                "requires_manual_approval": False,
                "email_type": "compliance_revoke",
                "ecosystem": eco_name
            })

            return {
                "id": email_msg.id,
                "account_id": account_meta.get("id"),
                "account_label": acc_label,
                "ecosystem": eco_name,
                "sender": email_msg.sender_email,
                "subject": email_msg.subject,
                "compliance_action": "REVOKED_AND_WIPED",
                "draft_created": True,
                "event_scheduled": False,
                "auto_sent": bool(sent_ok),
                "draft_content": del_draft
            }

        # 1b. MANDATORY CONSENT ARCHIVE ("I AGREE" via email)
        if compliance_intent == "consent_agree":
            logger.info(f"EXPLICIT CONSENT 'I AGREE' received from '{email_msg.sender_email}'")
            consent_entry = self.vault.log_consent(
                email=email_msg.sender_email,
                consent_text=f"Email Authorization: {email_msg.subject}",
                status="AUTHORIZED"
            )
            ack_draft = drafter.generate_consent_acknowledgment_email(original_subject=email_msg.subject)
            sent_ok = connector.send_email(
                recipient=email_msg.sender_email,
                subject=ack_draft["subject"],
                body=ack_draft["body"],
                reply_to_id=email_msg.thread_id or email_msg.id
            )
            self.audit_logger.log_workflow_execution({
                "account_id": account_meta.get("id"),
                "account_label": acc_label,
                "urgency": "normal",
                "meeting_time": None,
                "event_scheduled": False,
                "has_conflict": False,
                "draft_created": True,
                "auto_sent": bool(sent_ok),
                "is_autonomous_approved": True,
                "requires_manual_approval": False,
                "email_type": "compliance_consent",
                "ecosystem": eco_name
            })
            return {
                "id": email_msg.id,
                "account_id": account_meta.get("id"),
                "account_label": acc_label,
                "ecosystem": eco_name,
                "sender": email_msg.sender_email,
                "subject": email_msg.subject,
                "compliance_action": "AUTHORIZED",
                "consent_entry": consent_entry,
                "draft_created": True,
                "event_scheduled": False,
                "auto_sent": bool(sent_ok),
                "draft_content": ack_draft
            }

        calendar_result = None
        event_scheduled = False
        has_conflict = False
        escalation_triggered = False
        focus_blocks_count = 0
        invoice_extracted = False
        ooo_rescheduled = False
        role_handoff_triggered = False

        # 2. Confidence-Based Decision Routing
        meeting_conf = extracted.get("meeting_confidence", 0.0)
        is_autonomous_approved = meeting_conf >= 0.70
        requires_manual_approval = (0.35 <= meeting_conf < 0.70)

        # 3. Real-Time High-Urgency Escalation & Emergency Focus Slot
        if extracted.get("urgency") == "high":
            escalation_triggered = True
            self._dispatch_urgency_escalation(account_meta, email_msg, scheduler)
            focus_blocks_count += 1

        # 3b. CC-Escalation & Sentiment Drift War-Room Booking
        if extracted.get("requires_war_room"):
            escalation_triggered = True
            war_reason = f"Sentiment: {extracted.get('sentiment', {}).get('sentiment')}, CC Escalation: {extracted.get('cc_escalation', {}).get('is_cc_escalation')}"
            war_event = scheduler.schedule_war_room_sync(email_msg.subject, war_reason)
            if war_event:
                self.audit_logger.log_war_room({
                    "subject": email_msg.subject,
                    "sender": email_msg.sender_email,
                    "reason": war_reason,
                    "event_id": war_event.id,
                    "start_time": war_event.start_time.isoformat()
                })

        # 4. Out of Office (OOO) Auto-Rescheduling
        ooo_info = extracted.get("out_of_office", {})
        if ooo_info.get("is_ooo") and ooo_info.get("return_date"):
            shifted = scheduler.reschedule_conflicting_events_for_ooo(email_msg.sender_email, ooo_info["return_date"])
            if shifted:
                ooo_rescheduled = True
                logger.info(f"Shifted {len(shifted)} meetings for OOO attendee {email_msg.sender_email}")

        # 5. Task & Deadline Time-Blocking
        deliverables = extracted.get("deliverables", [])
        if deliverables:
            for deliv in deliverables:
                if deliv.get("deadline"):
                    block_ev = scheduler.schedule_focus_prep_block(deliv["task"], deliv["deadline"])
                    if block_ev:
                        focus_blocks_count += 1

        # 6. Invoice & Contract Extractor Pipeline
        inv_info = extracted.get("invoice_metadata", {})
        if inv_info.get("is_invoice"):
            invoice_extracted = True
            scheduler.schedule_payment_reminder(inv_info)
            self.audit_logger.log_invoice(inv_info)

        # Check if this email is a prospect demo inquiry or email to smartcal.systems@gmail.com (Zero-Call Sandbox Funnel)
        recipient_acc_email = account_meta.get("email", "").lower()
        is_smartcal_inbox = "smartcal.systems@gmail.com" in recipient_acc_email or "smartcal" in acc_label.lower()
        subj_body_lower = f"{email_msg.subject} {email_msg.body_text}".lower()
        is_demo_inquiry = bool(
            re.search(r"\b(demo|test drive|live demo)\b", subj_body_lower)
            or (is_smartcal_inbox and not extracted.get("selected_plan") and not compliance_intent)
        )

        if is_demo_inquiry:
            # ZERO-CALL SANDBOX MODE: Never schedule real calls that require our team to attend.
            sim_slot = extracted.get("proposed_datetime")
            if not sim_slot:
                now_utc = datetime.utcnow()
                sim_slot = (now_utc + timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0)
            sim_slot_str = sim_slot.strftime("%A, %B %d at %I:%M %p IST")

            calendar_result = {
                "scheduled": True,
                "is_simulation_only": True,
                "has_conflict": False,
                "title": "[SIMULATION PREVIEW ONLY] SmartCal Systems 60s Demo",
                "meeting_link": "https://meet.google.com/sim-smartcal-preview",
                "meeting_time": sim_slot_str,
                "alternative_slots": []
            }
            event_scheduled = True
            extracted["is_demo_simulation"] = True
            extracted["email_type"] = "demo_simulation"
        else:
            # 7. Calendar Event Creation & VIP Auto-Bump Engine
            vip_senders = [v.lower() for v in self.settings.get("vip_senders", [])]
            vip_domains = [d.lower() for d in self.settings.get("vip_domains", [])]
            sender_lower = email_msg.sender_email.lower()
            sender_dom = sender_lower.split("@")[-1] if "@" in sender_lower else ""
            is_vip = (sender_lower in vip_senders) or (sender_dom in vip_domains)

            if extracted.get("is_meeting_request") and extracted.get("proposed_datetime"):
                if is_vip:
                    # Attempt VIP Auto-Bump over internal meetings
                    bump_res = scheduler.bump_internal_meeting_for_vip(
                        vip_email=email_msg.sender_email,
                        vip_name=email_msg.sender_name,
                        requested_start=extracted["proposed_datetime"],
                        duration_minutes=extracted.get("duration_minutes", 45)
                    )
                    if bump_res.get("bumped"):
                        event_scheduled = True
                        calendar_result = {
                            "scheduled": True,
                            "has_conflict": False,
                            "event": bump_res["vip_event"],
                            "title": bump_res["vip_event"].title,
                            "meeting_link": bump_res["vip_event"].meeting_link,
                            "alternative_slots": [],
                            "vip_bumped": True
                        }
                        self.audit_logger.log_vip_bump({
                            "vip_email": email_msg.sender_email,
                            "vip_name": email_msg.sender_name,
                            "bumped_event": bump_res["bumped_event_title"],
                            "rescheduled_to": bump_res["rescheduled_slot"]
                        })
                    elif bump_res.get("scheduled"):
                        event_scheduled = True
                        calendar_result = {
                            "scheduled": True,
                            "has_conflict": False,
                            "event": bump_res["event"],
                            "title": bump_res["event"].title,
                            "meeting_link": bump_res["event"].meeting_link,
                            "alternative_slots": []
                        }
                    else:
                        calendar_result = scheduler.schedule_from_email_data(extracted, ecosystem=eco_name)
                        event_scheduled = calendar_result.get("scheduled", False)
                        has_conflict = calendar_result.get("has_conflict", False)
                else:
                    calendar_result = scheduler.schedule_from_email_data(extracted, ecosystem=eco_name)
                    event_scheduled = calendar_result.get("scheduled", False)
                    has_conflict = calendar_result.get("has_conflict", False)

        # 8. Cross-Inbox Role Handoff & Response Drafting
        is_exec = any(kw in acc_label.lower() or kw in account_meta.get("email", "").lower() for kw in ["exec", "executive", "ceo", "director"])
        if is_exec and extracted.get("role_intent") == "operations":
            ops_entry = None
            for o_id, o_ent in self.account_connectors.items():
                if any(kw in o_ent["meta"].get("label", "").lower() or kw in o_ent["meta"].get("email", "").lower() for kw in ["ops", "operations", "support", "client"]):
                    ops_entry = o_ent
                    break
            
            if ops_entry:
                ops_label = ops_entry["meta"].get("label", "Client Operations")
                ops_email = ops_entry["meta"].get("email", "ops@company.internal")
                reply_draft = drafter.generate_role_handoff_draft(
                    original_subject=email_msg.subject,
                    sender_name=email_msg.sender_name,
                    ops_contact=ops_email,
                    ops_label=ops_label,
                    issue_summary=email_msg.subject
                )
                role_handoff_triggered = True
                self.audit_logger.log_role_handoff({
                    "from_account": acc_label,
                    "to_account": ops_label,
                    "ops_contact": ops_email,
                    "sender": email_msg.sender_email,
                    "subject": email_msg.subject
                })
            else:
                reply_draft = drafter.generate_reply(
                    extracted_data=extracted,
                    calendar_result=calendar_result,
                    ecosystem=eco_name,
                    recipient_preferences=self.settings.get("recipient_preferences")
                )
        else:
            reply_draft = drafter.generate_reply(
                extracted_data=extracted,
                calendar_result=calendar_result,
                ecosystem=eco_name,
                recipient_preferences=self.settings.get("recipient_preferences")
            )

        # 9. Auto-Send Reply Directly via SMTP (Send ONLY ONCE per unread message)
        html_body = reply_draft.get("html_body")
        sent_ok = connector.send_email(
            recipient=email_msg.sender_email,
            subject=reply_draft["subject"],
            body=reply_draft["body"],
            reply_to_id=email_msg.thread_id or email_msg.id,
            html_body=html_body
        )
        draft_res = connector.create_draft_reply(
            original_email=email_msg,
            draft_subject=reply_draft["subject"],
            draft_body=reply_draft["body"],
            html_body=html_body
        )
        draft_info = {
            "success": sent_ok or draft_res.get("success", False),
            "status": "sent" if sent_ok else "drafted",
            "auto_sent": sent_ok,
            "draft_id": draft_res.get("draft_id")
        }

        # 10. Register in Follow-Up Tracker (for 48-hour No-Reply chaser loop)
        self.audit_logger.add_pending_followup(
            email_id=email_msg.id,
            recipient=email_msg.sender_email,
            subject=email_msg.subject,
            account_id=account_meta.get("id", "default")
        )

        # 11. Mark as read
        connector.mark_email_as_read(email_msg.id)

        # 12. Audit Record (DPDP Act Zero Private Data Retention: Only non-sensitive metadata stored on disk)
        audit_record = {
            "account_id": account_meta.get("id"),
            "account_label": acc_label,
            "urgency": extracted.get("urgency", "normal"),
            "meeting_time": extracted["proposed_datetime"].isoformat() if extracted.get("proposed_datetime") else None,
            "event_scheduled": event_scheduled,
            "has_conflict": has_conflict,
            "draft_created": bool(draft_info.get("success", False)),
            "auto_sent": bool(draft_info.get("auto_sent", False)),
            "is_autonomous_approved": is_autonomous_approved,
            "requires_manual_approval": requires_manual_approval,
            "meeting_confidence": meeting_conf,
            "email_type": extracted.get("email_type"),
            "ecosystem": eco_name
        }
        self.audit_logger.log_workflow_execution(audit_record)

        return {
            "id": email_msg.id,
            "account_id": account_meta.get("id"),
            "account_label": acc_label,
            "ecosystem": eco_name,
            "sender": email_msg.sender_email,
            "subject": email_msg.subject,
            "action_items": extracted["action_items"],
            "proposed_datetime": extracted["proposed_datetime"].isoformat() if extracted["proposed_datetime"] else None,
            "calendar_result": calendar_result,
            "event_scheduled": event_scheduled,
            "has_conflict": has_conflict,
            "escalation_triggered": escalation_triggered,
            "focus_blocks_scheduled": focus_blocks_count,
            "invoice_extracted": invoice_extracted,
            "ooo_rescheduled": ooo_rescheduled,
            "is_autonomous_approved": is_autonomous_approved,
            "requires_manual_approval": requires_manual_approval,
            "draft_created": bool(draft_info.get("success", False)),
            "draft_content": reply_draft,
            "draft_info": draft_info
        }

    def _dispatch_urgency_escalation(
        self,
        account_meta: Dict[str, Any],
        email_msg: EmailMessage,
        scheduler: UnifiedCalendarScheduler
    ) -> None:
        """Dispatch instant webhook escalation and block 30-minute emergency focus slot."""
        webhook_url = self.settings.get("escalation_webhook_url", "")
        payload = {
            "alert": "HIGH URGENCY EMAIL ESCALATION",
            "account": account_meta.get("label"),
            "from": email_msg.sender_email,
            "subject": email_msg.subject,
            "timestamp": datetime.utcnow().isoformat(),
            "action": "Blocked 30-min Emergency Focus Slot on Calendar"
        }

        # Auto-block emergency focus slot
        scheduler.schedule_emergency_focus_block(issue_subject=email_msg.subject, duration_minutes=30)

        # Dispatch webhook if configured
        if webhook_url:
            try:
                requests.post(webhook_url, json=payload, timeout=3.0)
                logger.info(f"Dispatched high-urgency escalation webhook to {webhook_url}")
            except Exception as e:
                logger.warning(f"Webhook dispatch failed: {e}")

        self.audit_logger.log_escalation(payload)

    def check_and_stage_followup_chasers(self, hours_threshold: float = 48.0) -> int:
        """Scan outbound tracked emails and stage polite follow-up drafts for threads awaiting a reply."""
        now = datetime.utcnow()
        chasers_staged = 0
        pending = self.audit_logger.get_pending_followups()

        for item in pending:
            if item.get("chased"):
                continue

            try:
                sent_at = datetime.fromisoformat(item["sent_at"])
                elapsed_hours = (now - sent_at).total_seconds() / 3600.0

                # If elapsed >= hours_threshold (or simulated test override)
                if elapsed_hours >= hours_threshold:
                    acc_id = item.get("account_id")
                    entry = self.account_connectors.get(acc_id)
                    if not entry:
                        entry = next(iter(self.account_connectors.values()), None)

                    if entry:
                        connector: BaseEcosystemConnector = entry["connector"]
                        drafter = ContextualEmailDrafter(sender_display_name=entry["meta"].get("display_name", "Assistant"))
                        chaser_draft = drafter.generate_followup_chaser(
                            original_subject=item["subject"],
                            recipient_name=item["recipient"],
                            days_waiting=int(elapsed_hours // 24) or 2
                        )
                        # Stage draft in mailbox
                        dummy_msg = EmailMessage(
                            id=f"followup_{item['email_id']}",
                            source_ecosystem=entry["meta"].get("ecosystem", "google"),
                            sender_name=item["recipient"],
                            sender_email=item["recipient"],
                            subject=chaser_draft["subject"],
                            date_received=now,
                            body_text=""
                        )
                        connector.create_draft_reply(
                            original_email=dummy_msg,
                            draft_subject=chaser_draft["subject"],
                            draft_body=chaser_draft["body"]
                        )
                        self.audit_logger.mark_followup_chased(item["email_id"])
                        chasers_staged += 1
                        logger.info(f"Staged 48h Follow-up Chaser draft to {item['recipient']} for '{item['subject']}'")
            except Exception as e:
                logger.warning(f"Error checking follow-up for {item.get('email_id')}: {e}")

        return chasers_staged

    def generate_pre_meeting_dossiers(self, window_minutes: int = 30) -> int:
        """Scan upcoming calendar events within 30 minutes and attach historical email dossiers."""
        now = datetime.utcnow()
        window_end = now + timedelta(minutes=window_minutes)
        dossiers_attached = 0
        all_connectors = self._get_all_connectors()

        for conn in all_connectors:
            events_attr = getattr(conn, "_calendar_events", None) or getattr(conn, "_mock_events", None)
            if not events_attr:
                continue

            for ev in events_attr:
                # Only attach dossiers to external meetings with attendees (skip internal focus blocks and payment reminders)
                if not ev.attendees or any(kw in ev.title for kw in ["URGENT FOCUS", "Focus / Prep", "Payment Due"]):
                    continue

                # If meeting is starting within window
                if now <= ev.start_time <= window_end and "PRE-MEETING CONTEXT DOSSIER" not in ev.description:
                    dossier_bullets = []
                    # Search recent audit records for discussions with these attendees
                    recent_records = self.audit_logger.get_recent_records(limit=100)
                    for att in ev.attendees:
                        matched_records = [r for r in recent_records if att.lower() in r.get("sender", "").lower()]
                        for mr in matched_records[:2]:
                            dossier_bullets.append(f"• Discussion with {att} on '{mr.get('subject')}':")
                            for item in mr.get("action_items", [])[:2]:
                                dossier_bullets.append(f"    - {item}")

                    if not dossier_bullets:
                        dossier_bullets.append("• Verified attendees and calendar slot confirmed.")
                        dossier_bullets.append(f"• Agenda Items: {ev.title}")

                    dossier_text = "\n".join(dossier_bullets)
                    ev.description = f"{ev.description}\n\n--- 📑 PRE-MEETING CONTEXT DOSSIER ---\n{dossier_text}"
                    self.audit_logger.increment_dossier_count()
                    dossiers_attached += 1
                    logger.info(f"Attached Pre-Meeting Context Dossier to upcoming event '{ev.title}'")

        return dossiers_attached

    def process_ended_meetings_and_dispatch_mom(self, window_minutes: int = 60) -> int:
        """Scan concluded calendar events, retrieve transcripts, extract action items, and stage MoM drafts."""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        moms_dispatched = 0
        all_connectors = self._get_all_connectors()

        for conn in all_connectors:
            events_attr = getattr(conn, "_calendar_events", None) or getattr(conn, "_mock_events", None)
            if not events_attr:
                continue

            for ev in events_attr:
                # If meeting ended recently and MoM not yet dispatched
                if window_start <= ev.end_time <= now and "[MoM Dispatched]" not in ev.description:
                    transcript = conn.fetch_meeting_transcript(ev.id)
                    if transcript:
                        mom_data = self.extractor.extract_mom_and_action_owners(transcript)
                        drafter = ContextualEmailDrafter()
                        mom_email = drafter.generate_mom_email(
                            event_title=ev.title,
                            attendees=ev.attendees,
                            mom_data=mom_data
                        )

                        dummy_msg = EmailMessage(
                            id=f"mom_{ev.id}",
                            source_ecosystem=ev.source_ecosystem,
                            sender_name="Meeting Attendees",
                            sender_email=ev.attendees[0] if ev.attendees else "team@company.internal",
                            subject=mom_email["subject"],
                            date_received=now,
                            body_text=""
                        )
                        conn.create_draft_reply(
                            original_email=dummy_msg,
                            draft_subject=mom_email["subject"],
                            draft_body=mom_email["body"]
                        )
                        ev.description += "\n[MoM Dispatched]: Minutes of meeting drafted to all attendees."
                        self.audit_logger.log_mom_dispatch({
                            "event_id": ev.id,
                            "event_title": ev.title,
                            "attendees": ev.attendees,
                            "decisions_count": len(mom_data.get("decisions", [])),
                            "action_items_count": len(mom_data.get("action_items", []))
                        })
                        moms_dispatched += 1
                        logger.info(f"Dispatched MoM email for concluded event '{ev.title}'")

        return moms_dispatched

    def check_live_meeting_attendance_and_recover(self) -> int:
        """Monitor active meetings 7 minutes past start time and send no-show recovery check-ins."""
        now = datetime.utcnow()
        recoveries_sent = 0
        all_connectors = self._get_all_connectors()

        for conn in all_connectors:
            events_attr = getattr(conn, "_calendar_events", None) or getattr(conn, "_mock_events", None)
            if not events_attr:
                continue

            for ev in events_attr:
                started_mins_ago = (now - ev.start_time).total_seconds() / 60.0
                # If meeting started 7+ mins ago and is still active
                if 7.0 <= started_mins_ago <= 30.0 and ev.end_time > now:
                    if "[No-Show Checked]" in ev.description:
                        continue

                    attendance = conn.check_meeting_attendance(ev.id)
                    missing_attendees = attendance.get("missing", [])

                    if missing_attendees:
                        scheduler = UnifiedCalendarScheduler(conn, all_connectors)
                        alt_slots = scheduler.find_alternative_slots(now + timedelta(days=1), count=3)
                        drafter = ContextualEmailDrafter()

                        for missing in missing_attendees:
                            checkin_draft = drafter.generate_noshow_recovery_email(
                                event_title=ev.title,
                                attendee_name=missing.split("@")[0].capitalize(),
                                attendee_email=missing,
                                alternative_slots=alt_slots
                            )
                            dummy_msg = EmailMessage(
                                id=f"noshow_{ev.id}_{missing}",
                                source_ecosystem=ev.source_ecosystem,
                                sender_name=missing,
                                sender_email=missing,
                                subject=checkin_draft["subject"],
                                date_received=now,
                                body_text=""
                            )
                            conn.create_draft_reply(
                                original_email=dummy_msg,
                                draft_subject=checkin_draft["subject"],
                                draft_body=checkin_draft["body"]
                            )
                            self.audit_logger.log_noshow_recovery({
                                "event_id": ev.id,
                                "event_title": ev.title,
                                "missing_attendee": missing,
                                "rescheduling_slots_offered": [s.get("formatted") for s in alt_slots]
                            })
                            recoveries_sent += 1
                            logger.info(f"Fired live No-Show Recovery email to {missing} for '{ev.title}'")

                        ev.description += "\n[No-Show Checked]: Fired recovery check-in to absent attendees."

        return recoveries_sent

    def run_calendar_defragmentation(self, target_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Execute calendar defragmentation run across connected calendars."""
        dt = target_date or (datetime.utcnow() + timedelta(days=1))
        all_connectors = self._get_all_connectors()
        lead_conn = all_connectors[0] if all_connectors else None
        if not lead_conn:
            return {"defragmented": False, "gaps_found": 0}

        scheduler = UnifiedCalendarScheduler(lead_conn, all_connectors)
        defrag_result = scheduler.defragment_calendar_schedule(dt)
        self.audit_logger.log_defragmentation(defrag_result)
        logger.info(f"Calendar Defragmentation for {dt.strftime('%Y-%m-%d')}: Reclaimed {defrag_result['minutes_reclaimed']}m of dead time.")
        return defrag_result
