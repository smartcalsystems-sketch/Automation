"""Comprehensive Unit and Integration Test Suite for SmartCal Systems Automation Agent."""
import unittest
from datetime import datetime, timedelta

from config.settings import DEFAULT_SETTINGS
from auth.vault import CredentialVault
from auth.rdp_session import RDPSessionManager
from connectors.mock_connector import MockEcosystemConnector
from connectors.google_connector import GoogleWorkspaceConnector
from connectors.base_connector import EmailMessage, CalendarEvent
from engine.nlp_parser import EmailEntityExtractor
from engine.email_drafter import ContextualEmailDrafter
from engine.calendar_scheduler import UnifiedCalendarScheduler
from pipeline.workflow_manager import AutomationWorkflowManager


from pathlib import Path
import os

TEST_VAULT_FILE = Path(__file__).resolve().parent / "test_vault.json"


class TestAutomationAgent(unittest.TestCase):

    def setUp(self):
        if TEST_VAULT_FILE.exists():
            TEST_VAULT_FILE.unlink()
        self.vault = CredentialVault(vault_file=TEST_VAULT_FILE)
        self.extractor = EmailEntityExtractor(default_tz="UTC")
        self.drafter = ContextualEmailDrafter()

    def tearDown(self):
        if TEST_VAULT_FILE.exists():
            TEST_VAULT_FILE.unlink()

    def test_vault_encryption_and_decryption(self):
        """Verify credential storage obfuscation and recovery."""
        test_creds = {
            "google": {"email": "test@gmail.com", "app_password": "supersecretpassword123"},
            "m365": {"email": "test@outlook.com", "password": "m365password456"},
            "rdp": {"host": "10.0.0.5", "username": "admin"}
        }
        self.vault.save_credentials(test_creds)
        loaded = self.vault.get_credentials()
        self.assertEqual(loaded["google"]["email"], "test@gmail.com")
        self.assertEqual(loaded["google"]["app_password"], "supersecretpassword123")
        self.assertEqual(loaded["m365"]["password"], "m365password456")

    def test_entity_extraction_dates_and_actions(self):
        """Test NLP parser extraction of action items and meeting slots."""
        body = (
            "Hi team,\n"
            "Could we meet on October 15, 2026 at 3:00 PM UTC for 30 minutes?\n\n"
            "Action items:\n"
            "- Finalize Kubernetes deployment scripts\n"
            "- Verify OAuth token renewal logic\n\n"
            "Best,\nJohn"
        )
        data = self.extractor.extract_all(
            subject="Kubernetes Deployment Review",
            body_text=body,
            sender_name="John Doe",
            sender_email="john@example.com"
        )
        self.assertTrue(data["is_meeting_request"])
        self.assertEqual(data["duration_minutes"], 30)
        self.assertIsNotNone(data["proposed_datetime"])
        self.assertEqual(data["proposed_datetime"].year, 2026)
        self.assertEqual(data["proposed_datetime"].month, 10)
        self.assertEqual(data["proposed_datetime"].day, 15)
        self.assertEqual(len(data["action_items"]), 2)
        self.assertIn("Finalize Kubernetes deployment scripts", data["action_items"])

    def test_calendar_scheduling_and_conflict_handling(self):
        """Test conflict detection and alternative slot generation."""
        mock_connector = MockEcosystemConnector(ecosystem="google")
        scheduler = UnifiedCalendarScheduler(mock_connector)
        now = datetime.utcnow()

        # Slot overlapping with pre-existing All-Hands (15:00 - 16:00 tomorrow)
        conflict_time = (now + timedelta(days=1)).replace(hour=15, minute=15, second=0, microsecond=0)
        email_data = {
            "is_meeting_request": True,
            "proposed_datetime": conflict_time,
            "proposed_end_time": conflict_time + timedelta(minutes=45),
            "duration_minutes": 45,
            "suggested_title": "Project Sync",
            "attendees": ["guest@partner.com"],
            "action_items": ["Discuss API keys"]
        }

        # Schedule should detect conflict
        result = scheduler.schedule_from_email_data(email_data, ecosystem="google")
        self.assertTrue(result["has_conflict"])
        self.assertFalse(result["scheduled"])
        self.assertIn("Weekly Engineering All-Hands", result["conflicting_event"])

        # Drafter should include conflict alternatives
        draft = self.drafter.generate_reply(email_data, calendar_result=result, ecosystem="google")
        self.assertIn("existing calendar hold", draft["body"])
        self.assertTrue("alternative slots" in draft["body"] or "alternative times" in draft["body"])

    def test_clean_scheduling_without_conflicts(self):
        """Test clean meeting slot booking with Google Meet link."""
        mock_connector = MockEcosystemConnector(ecosystem="google")
        scheduler = UnifiedCalendarScheduler(mock_connector)
        now = datetime.utcnow()

        clean_time = (now + timedelta(days=5)).replace(hour=10, minute=0, second=0, microsecond=0)
        email_data = {
            "is_meeting_request": True,
            "proposed_datetime": clean_time,
            "proposed_end_time": clean_time + timedelta(minutes=30),
            "duration_minutes": 30,
            "suggested_title": "Clean Architecture Sync",
            "attendees": ["architect@enterprise.org"],
            "action_items": ["Review microservices boundary"]
        }

        result = scheduler.schedule_from_email_data(email_data, ecosystem="google")
        self.assertFalse(result["has_conflict"])
        self.assertTrue(result["scheduled"])
        self.assertTrue(result["meeting_link"].startswith("https://meet.google.com/"))

        # Drafter confirmation
        draft = self.drafter.generate_reply(email_data, calendar_result=result, ecosystem="google")
        self.assertIn("confirmed our calendar", draft["body"])
        self.assertIn("Google Meet Meeting Link", draft["body"])

    def test_m365_teams_scheduling(self):
        """Test M365 Outlook meeting scheduling with Teams link."""
        mock_connector = MockEcosystemConnector(ecosystem="m365")
        scheduler = UnifiedCalendarScheduler(mock_connector)
        now = datetime.utcnow()

        meeting_time = (now + timedelta(days=4)).replace(hour=16, minute=0, second=0, microsecond=0)
        email_data = {
            "is_meeting_request": True,
            "proposed_datetime": meeting_time,
            "proposed_end_time": meeting_time + timedelta(minutes=60),
            "duration_minutes": 60,
            "suggested_title": "Teams Quarterly Review",
            "attendees": ["director@m365org.com"],
            "action_items": ["Q3 KPI Assessment"]
        }

        result = scheduler.schedule_from_email_data(email_data, ecosystem="m365")
        self.assertTrue(result["scheduled"])
        self.assertTrue("teams.microsoft.com" in result["meeting_link"])

        draft = self.drafter.generate_reply(email_data, calendar_result=result, ecosystem="m365")
        self.assertIn("Microsoft Teams Meeting Link", draft["body"])

    def test_multi_account_vault_operations(self):
        """Verify adding, listing, pausing, and deleting multiple accounts."""
        acc1_id = self.vault.upsert_account({
            "label": "Work Gmail",
            "ecosystem": "google",
            "email": "work@company.com",
            "app_password": "secret_work_pass",
            "enabled": True
        })
        acc2_id = self.vault.upsert_account({
            "label": "Personal Gmail",
            "ecosystem": "google",
            "email": "personal@gmail.com",
            "app_password": "secret_personal_pass",
            "enabled": True
        })
        acc3_id = self.vault.upsert_account({
            "label": "Corporate M365",
            "ecosystem": "m365",
            "email": "corp@enterprise.org",
            "password": "secret_m365_pass",
            "enabled": True
        })

        accounts = self.vault.list_accounts()
        self.assertEqual(len(accounts), 3)

        # Check decryption
        acc1 = self.vault.get_account(acc1_id)
        self.assertEqual(acc1["app_password"], "secret_work_pass")

        # Pause account 2
        self.vault.toggle_account(acc2_id, False)
        enabled_only = self.vault.list_accounts(enabled_only=True)
        self.assertEqual(len(enabled_only), 2)

        # Delete account 3
        self.vault.delete_account(acc3_id)
        self.assertEqual(len(self.vault.list_accounts()), 2)

    def test_workflow_manager_multi_account_simulation(self):
        """Test multi-account pipeline execution across multiple simulated accounts."""
        wm = AutomationWorkflowManager(force_simulation=True)
        summary = wm.process_all_ecosystems()
        self.assertEqual(summary["status"], "completed")
        self.assertGreaterEqual(summary["accounts_scanned"], 2)
        self.assertGreater(summary["emails_scanned"], 0)
        self.assertGreater(summary["drafts_created"], 0)
        self.assertGreater(summary["events_scheduled"], 0)

        # Test targeting a single account
        single_acc_id = list(wm.account_connectors.keys())[0]
        single_summary = wm.process_all_ecosystems(target_account_id=single_acc_id)
        self.assertEqual(single_summary["accounts_scanned"], 1)

    def test_every_incoming_email_generates_draft_reply(self):
        """Verify that 100% of all incoming emails generate a draft reply."""
        wm = AutomationWorkflowManager(force_simulation=True)
        summary = wm.process_all_ecosystems()

        # Assert every single processed email has a draft created
        self.assertGreater(summary["emails_processed"], 0)
        self.assertEqual(summary["emails_processed"], summary["drafts_created"])

        # Check drafts content across different categories
        items = summary["items"]
        subjects = [it["subject"] for it in items]
        
        # Verify deliverable commitment email got a tailored draft
        deliv_items = [it for it in items if "Deliverable" in it["subject"]]
        self.assertTrue(len(deliv_items) > 0)
        deliv_draft = deliv_items[0]["draft_content"]
        self.assertTrue(deliv_draft["subject"].startswith("Re:"))
        self.assertIn("logged the deliverable commitment", deliv_draft["body"])

        # Verify urgent emergency email got priority draft
        urgent_items = [it for it in items if "CRITICAL" in it["subject"]]
        self.assertTrue(len(urgent_items) > 0)
        urgent_draft = urgent_items[0]["draft_content"]
        self.assertIn("HIGH URGENCY", urgent_draft["body"])

    def test_auto_detect_and_simple_account_setup(self):
        """Verify that user only needs to supply Email and Password."""
        from auth.account_detector import auto_detect_email_service
        
        # Test Gmail detection
        g_detect = auto_detect_email_service("steve.jobs@gmail.com")
        self.assertEqual(g_detect["ecosystem"], "google")
        self.assertEqual(g_detect["imap_server"], "imap.gmail.com")
        self.assertEqual(g_detect["meeting_provider"], "Google Meet")

        # Test M365 detection
        m_detect = auto_detect_email_service("satya.nadella@outlook.com")
        self.assertEqual(m_detect["ecosystem"], "m365")
        self.assertEqual(m_detect["imap_server"], "outlook.office365.com")
        self.assertEqual(m_detect["meeting_provider"], "Microsoft Teams")

        # Test simple account registration with ONLY email and password
        acc = self.vault.add_simple_account("testuser@gmail.com", "app_pass_999")
        self.assertEqual(acc["email"], "testuser@gmail.com")
        self.assertEqual(acc["ecosystem"], "google")
        
        # Verify in vault
        saved = self.vault.get_account(acc["id"])
        self.assertIsNotNone(saved)
        self.assertEqual(saved["app_password"], "app_pass_999")

    def test_cross_account_free_busy_and_slot_negotiation(self):
        """Pillar 1: Cross-account conflict checking and 3 alternative slots."""
        google_conn = MockEcosystemConnector(ecosystem="google")
        m365_conn = MockEcosystemConnector(ecosystem="m365")
        
        scheduler = UnifiedCalendarScheduler(connector=m365_conn, all_connectors=[google_conn, m365_conn])
        now = datetime.utcnow()

        # Slot conflicting with Google All-Hands (15:00 - 16:00 tomorrow)
        conflict_time = (now + timedelta(days=1)).replace(hour=15, minute=15, second=0, microsecond=0)
        email_data = {
            "is_meeting_request": True,
            "proposed_datetime": conflict_time,
            "proposed_end_time": conflict_time + timedelta(minutes=45),
            "duration_minutes": 45,
            "suggested_title": "Executive Review",
            "attendees": ["partner@company.com"],
            "action_items": []
        }

        # Cross-account check should detect conflict on Google calendar while scheduling on M365
        result = scheduler.schedule_from_email_data(email_data, ecosystem="m365")
        self.assertTrue(result["has_conflict"])
        self.assertFalse(result["scheduled"])
        self.assertGreaterEqual(len(result["alternative_slots"]), 2)

        # Drafter should format these alternative slots
        draft = self.drafter.generate_reply(email_data, calendar_result=result, ecosystem="m365")
        self.assertIn("alternative slots work for you", draft["body"])

    def test_urgent_escalation_and_emergency_focus(self):
        """Pillar 2: Real-time high-urgency escalation and 30-min emergency focus block."""
        extractor = EmailEntityExtractor()
        body = "CRITICAL EMERGENCY: Urgent Database Failover Required ASAP. Production is down."
        urgency = extractor.detect_urgency("CRITICAL EMERGENCY", body)
        self.assertEqual(urgency, "high")

        mock_conn = MockEcosystemConnector(ecosystem="google")
        scheduler = UnifiedCalendarScheduler(mock_conn)
        focus_event = scheduler.schedule_emergency_focus_block("Urgent Database Failover", duration_minutes=30)
        self.assertIsNotNone(focus_event)
        self.assertIn("URGENT FOCUS", focus_event.title)

    def test_deliverable_commitments_and_focus_prep(self):
        """Pillar 2: Task deliverable extraction and focus prep time-blocking."""
        extractor = EmailEntityExtractor()
        body = "I will share the architecture deck by Friday EOD for the review."
        commitments = extractor.extract_deliverable_commitments(body)
        self.assertGreaterEqual(len(commitments), 1)
        self.assertIn("share", commitments[0]["task"].lower())

        mock_conn = MockEcosystemConnector(ecosystem="google")
        scheduler = UnifiedCalendarScheduler(mock_conn)
        prep_event = scheduler.schedule_focus_prep_block(commitments[0]["task"], commitments[0]["deadline"])
        self.assertIsNotNone(prep_event)
        self.assertIn("Focus / Prep", prep_event.title)

    def test_invoice_extraction_and_payment_reminder(self):
        """Pillar 3: Invoice metadata parsing and payment due reminder."""
        extractor = EmailEntityExtractor()
        body = "Invoice #INV-2026-904 from CloudServices Inc. Amount Due: $4,850.00 USD. Due Date: October 25, 2026."
        inv_data = extractor.extract_invoice_metadata("Invoice Notice", body)
        self.assertTrue(inv_data["is_invoice"])
        self.assertEqual(inv_data["invoice_number"], "INV-2026-904")
        self.assertEqual(inv_data["amount"], 4850.0)

        mock_conn = MockEcosystemConnector(ecosystem="google")
        scheduler = UnifiedCalendarScheduler(mock_conn)
        rem_event = scheduler.schedule_payment_reminder(inv_data)
        self.assertIsNotNone(rem_event)
        self.assertIn("Payment Due", rem_event.title)

    def test_ooo_detection_and_meeting_shift(self):
        """Pillar 3: OOO auto-reply detection and meeting shift past return date."""
        extractor = EmailEntityExtractor()
        body = "I am currently out of office on annual leave. I will be returning to the office on October 15, 2026."
        ooo_info = extractor.detect_out_of_office("Out of Office: Emily Zhao", body)
        self.assertTrue(ooo_info["is_ooo"])
        self.assertIsNotNone(ooo_info["return_date"])

        mock_conn = MockEcosystemConnector(ecosystem="google")
        now = datetime.utcnow()
        # Seed an event during OOO period
        mock_conn._calendar_events.append(CalendarEvent(
            id="ooo_conflict_event",
            source_ecosystem="google",
            title="Design Review with Emily",
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
            attendees=["emily.zhao@venturecap.com"],
            description="Discuss design"
        ))

        scheduler = UnifiedCalendarScheduler(mock_conn, [mock_conn])
        shifted = scheduler.reschedule_conflicting_events_for_ooo("emily.zhao@venturecap.com", ooo_info["return_date"])
        self.assertGreaterEqual(len(shifted), 1)

    def test_pre_meeting_context_dossier(self):
        """Pillar 1: Pre-meeting context dossier generation 30 minutes prior."""
        wm = AutomationWorkflowManager(force_simulation=True)
        count = wm.generate_pre_meeting_dossiers(window_minutes=30)
        self.assertGreaterEqual(count, 1)

    def test_followup_chaser_generation(self):
        """Pillar 2: Automated 48-hour follow-up chaser generation."""
        chaser = self.drafter.generate_followup_chaser("Q4 Architecture Review", "Sarah Jenkins", days_waiting=2)
        self.assertIn("Re: Q4 Architecture Review", chaser["subject"])
        self.assertIn("Checking in to see if you have had an opportunity", chaser["body"])


    def test_ooo_does_not_trigger_high_urgency(self):
        """Pillar 2 & 3: Ensure OOO disclaimer boilerplate does not trigger false high-urgency escalation."""
        extractor = EmailEntityExtractor()
        body = (
            "I am currently out of office on annual leave with limited access to email.\n"
            "I will be returning to the office on October 15, 2026.\n"
            "For urgent queries, please contact team@venturecap.com."
        )
        data = extractor.extract_all(
            subject="Out of Office: Emily Zhao on Annual Leave",
            body_text=body,
            sender_name="Emily Zhao",
            sender_email="emily.zhao@venturecap.com"
        )
        self.assertTrue(data["out_of_office"]["is_ooo"])
        self.assertNotEqual(data["urgency"], "high")
        self.assertEqual(data["urgency"], "normal")

    def test_time_and_communication_audit_metrics(self):
        """Pillar 4: Verify aggregation of time & communication audit in audit_logger."""
        from pipeline.audit_logger import AuditLogger
        logger = AuditLogger()
        audit_data = logger.get_time_and_communication_audit()
        self.assertIn("domain_meeting_hours", audit_data)
        self.assertIn("autonomous_rate_percent", audit_data)
        self.assertIn("avg_turnaround_seconds", audit_data)
        self.assertIn("total_emails_handled", audit_data)


    def test_post_meeting_transcript_to_mom_pipeline(self):
        """Advanced 1: Post-meeting transcript parsing into decisions, owners, and MoM email."""
        extractor = EmailEntityExtractor()
        transcript = (
            "Sarah Jenkins: Let's finalize the Q4 cloud security deliverables.\n"
            "David Chen: Key decision: We decided to enforce AES-256 for all at-rest credentials.\n"
            "Sarah Jenkins: Action item: Sarah will deliver the updated Terraform scripts by Friday EOD.\n"
            "David Chen: And I will complete the security audit report before Monday morning."
        )
        mom_data = extractor.extract_mom_and_action_owners(transcript)
        self.assertGreaterEqual(len(mom_data["decisions"]), 1)
        self.assertGreaterEqual(len(mom_data["action_items"]), 2)
        self.assertEqual(mom_data["action_items"][0]["owner"], "Sarah")

        drafter = ContextualEmailDrafter()
        mom_email = drafter.generate_mom_email(
            event_title="Q4 Cloud Architecture Sync",
            attendees=["sarah@acme.com", "david@corp.com"],
            mom_data=mom_data
        )
        self.assertIn("Minutes of Meeting", mom_email["subject"])
        self.assertIn("KEY DECISIONS", mom_email["body"])
        self.assertIn("ACTION ITEMS & OWNERS", mom_email["body"])

    def test_live_noshow_autorecovery(self):
        """Advanced 1: Live no-show detection and auto-recovery check-in."""
        wm = AutomationWorkflowManager(force_simulation=True)
        count = wm.check_live_meeting_attendance_and_recover()
        self.assertGreaterEqual(count, 1)

    def test_cross_inbox_role_handoff(self):
        """Advanced 2: Cross-inbox role-based handoff from executive to operations."""
        extractor = EmailEntityExtractor()
        role_intent = extractor.detect_role_intent(
            subject="Urgent: Production DNS & Billing Access Provisioning Issue",
            body_text="We have a technical provisioning error and ticket access problem."
        )
        self.assertEqual(role_intent, "operations")

        drafter = ContextualEmailDrafter()
        handoff_draft = drafter.generate_role_handoff_draft(
            original_subject="Urgent: DNS Access Issue",
            sender_name="Jason Miller",
            ops_contact="ops@company.internal",
            ops_label="Client Operations"
        )
        self.assertIn("Client Operations", handoff_draft["body"])
        self.assertIn("ops@company.internal", handoff_draft["body"])

    def test_sentiment_drift_and_cc_escalation_war_room(self):
        """Advanced 2: Frustrated sentiment and CC-escalation detection triggering internal war room."""
        extractor = EmailEntityExtractor()
        sentiment = extractor.detect_sentiment_drift(
            subject="Re: Critical Delays",
            body_text="The current delays are completely unacceptable and unresolved. We are losing patience."
        )
        self.assertTrue(sentiment["is_negative"])
        self.assertEqual(sentiment["sentiment"], "frustrated")

        cc_esc = extractor.detect_cc_escalation(
            current_attendees=["dev@client.com", "vp-engineering@client.com", "legal@client.com"],
            prior_attendees=["dev@client.com"]
        )
        self.assertTrue(cc_esc["is_cc_escalation"])
        self.assertGreaterEqual(len(cc_esc["senior_stakeholders_added"]), 1)

        # Trigger War-Room Booking
        mock_conn = MockEcosystemConnector(ecosystem="google")
        scheduler = UnifiedCalendarScheduler(mock_conn, [mock_conn])
        war_event = scheduler.schedule_war_room_sync(
            issue_subject="Critical Delays on API",
            escalation_reason="Frustrated sentiment + VP added to CC"
        )
        self.assertIsNotNone(war_event)
        self.assertIn("INTERNAL WAR-ROOM", war_event.title)

    def test_vip_auto_bump_engine(self):
        """Advanced 3: VIP Auto-Bump engine rescheduling internal meeting for VIP client."""
        now = datetime.utcnow()
        mock_conn = MockEcosystemConnector(ecosystem="google")
        # Add internal 1:1 that conflicts with target slot
        target_slot = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
        mock_conn._calendar_events.append(CalendarEvent(
            id="internal_1on1_to_bump",
            source_ecosystem="google",
            title="Internal 1:1 Sync with Alex",
            start_time=target_slot,
            end_time=target_slot + timedelta(minutes=45),
            attendees=["alex@company.internal"],
            description="Weekly 1:1"
        ))

        scheduler = UnifiedCalendarScheduler(mock_conn, [mock_conn])
        bump_res = scheduler.bump_internal_meeting_for_vip(
            vip_email="sarah.jenkins@acmepartners.com",
            vip_name="Sarah Jenkins",
            requested_start=target_slot,
            duration_minutes=45
        )
        self.assertTrue(bump_res["bumped"])
        self.assertTrue(bump_res["scheduled"])
        self.assertIn("Internal 1:1", bump_res["bumped_event_title"])

    def test_swiss_cheese_calendar_defragmentation(self):
        """Advanced 3: Consolidate awkward 15-30 minute gaps to reclaim deep-work blocks."""
        now = datetime.utcnow()
        mock_conn = MockEcosystemConnector(ecosystem="google")
        day_target = now + timedelta(days=2)
        m1_start = day_target.replace(hour=10, minute=0, second=0, microsecond=0)
        m1_end = m1_start + timedelta(minutes=30)
        # Awkward 20 minute gap
        m2_start = m1_end + timedelta(minutes=20)
        m2_end = m2_start + timedelta(minutes=30)

        mock_conn._calendar_events.extend([
            CalendarEvent(id="defrag_ev1", source_ecosystem="google", title="Project Review", start_time=m1_start, end_time=m1_end, attendees=["guest@partner.com"], description="Review"),
            CalendarEvent(id="defrag_ev2", source_ecosystem="google", title="Internal Standup Sync", start_time=m2_start, end_time=m2_end, attendees=["team@company.internal"], description="Sync")
        ])

        scheduler = UnifiedCalendarScheduler(mock_conn, [mock_conn])
        defrag_data = scheduler.defragment_calendar_schedule(day_target)
        self.assertGreaterEqual(defrag_data["gaps_found"], 1)
        self.assertGreaterEqual(defrag_data["minutes_reclaimed"], 15)

    def test_human_in_the_loop_style_learner(self):
        """Advanced 4: Human-in-the-loop manual edit logging and adaptive style learning."""
        from pipeline.audit_logger import AuditLogger
        audit = AuditLogger()
        audit.log_draft_human_edit(
            recipient="sarah.jenkins@acmepartners.com",
            original="Thank you for reaching out. Here are five detailed paragraphs about the architecture.",
            edited="Thanks Sarah, looks great. Confirmed for Thursday.",
            diff_summary="Shortened from 85 to 48 chars"
        )
        recent_edits = audit.get_draft_human_edits(limit=5)
        self.assertGreaterEqual(len(recent_edits), 1)
        self.assertEqual(recent_edits[0]["recipient"], "sarah.jenkins@acmepartners.com")

    def test_circuit_breaker_pause_and_reset(self):
        """Advanced 4: Vault Credential Circuit Breaker tripping and reset."""
        mock_conn = MockEcosystemConnector(ecosystem="google")
        self.assertFalse(mock_conn.is_circuit_open())
        mock_conn.trip_circuit("API Rate Limit 429: Exceeded quota")
        self.assertTrue(mock_conn.is_circuit_open())
        self.assertEqual(mock_conn.circuit_state, "OPEN")
        self.assertIn("Rate Limit", mock_conn.circuit_reason)

        # Reset
        mock_conn.reset_circuit()
        self.assertFalse(mock_conn.is_circuit_open())
        self.assertEqual(mock_conn.circuit_state, "CLOSED")


    def test_smartcal_systems_branding_and_signature(self):
        """Requirement 1: Verify complete removal of Antigravity and adoption of SmartCal Systems."""
        drafter = ContextualEmailDrafter()
        reply = drafter.generate_reply({
            "sender_name": "John Doe",
            "subject": "Quick sync",
            "email_type": "inquiry"
        })
        self.assertNotIn("Antigravity", reply["body"])
        self.assertIn("Best regards,\nSmartCal Systems\nAutomated Email & Calendar Scheduling Engine", reply["body"])

        # Test meeting title format
        extractor = EmailEntityExtractor()
        title = extractor.generate_meeting_title(subject="Product Demo", intent={}, sender_name="John Doe")
        self.assertEqual(title, "Calendar Invitation: SmartCal Systems Live Demo & Consultation")

    def test_strictly_block_system_and_noreply_emails(self):
        """Requirement 2: Strictly block system and no-reply emails from processing."""
        from connectors.google_connector import is_system_or_noreply

        # Senders that must be blocked
        blocked_senders = [
            ("no-reply@accounts.google.com", "Security alert for your account"),
            ("noreply@company.com", "Your statement is ready"),
            ("support@google.com", "Notice of updates"),
            ("alert@accounts.google", "Action required"),
            ("mailer-daemon@mx.google.com", "Delivery failure"),
            ("service@microsoft.com", "Your subscription invoice"),
            ("security@vault.io", "Sign-in attempt detected")
        ]
        for sender, subject in blocked_senders:
            self.assertTrue(
                is_system_or_noreply(sender, subject),
                f"Failed to block system email: {sender} / {subject}"
            )

        # Subjects that must be blocked regardless of sender
        blocked_subjects = [
            ("admin@unknown-domain.com", "Critical Security alert for your Google Account"),
            ("support@external.com", "Your 2-Step Verification code is 123456")
        ]
        for sender, subject in blocked_subjects:
            self.assertTrue(
                is_system_or_noreply(sender, subject),
                f"Failed to block subject: {subject}"
            )

        # Legitimate humans that must NOT be blocked
        allowed = [
            ("sarah.jenkins@acmepartners.com", "Q4 Strategic Review"),
            ("alex.rivera@fintechglobal.org", "Database failover discussion"),
            ("client@techscale.io", "Demo scheduling call")
        ]
        for sender, subject in allowed:
            self.assertFalse(
                is_system_or_noreply(sender, subject),
                f"Incorrectly blocked valid email: {sender} / {subject}"
            )

    def test_self_selling_demo_and_pricing_plans_in_reply(self):
        """Requirement 4: Confirm inquiry + Google Meet slot + 3 pricing plans + CTA."""
        drafter = ContextualEmailDrafter()
        reply = drafter.generate_reply({
            "sender_name": "Michael Scott",
            "subject": "Proposal Discussion",
            "email_type": "inquiry",
            "urgency": "normal"
        })
        body = reply["body"]

        # 1. Inquiry Confirmation & Urgency & Proposed Slot
        self.assertIn("Thank you for reaching out. I have confirmed your inquiry regarding 'Proposal Discussion' [Urgency: NORMAL].", body)
        self.assertIn("Proposed Google Meet Slot:", body)

        # 2. How SmartCal Systems Works (3 bullet points)
        self.assertIn("How SmartCal Systems Works (24/7 Inbox-to-Calendar Automation in 60 Seconds):", body)
        self.assertIn("Instant Triage:", body)
        self.assertIn("Autonomous Booking:", body)
        self.assertIn("24/7 Follow-Ups:", body)

        # 3. Transparent Pricing Plans
        self.assertIn("Plan 1: 48-Hour Free Live Trial (₹0)", body)
        self.assertIn("Plan 2: Solo Inbox Setup (₹2,999 One-Time)", body)
        self.assertIn("Plan 3: Multi-Account Agency Pro — Up to 5 Inboxes + Follow-Up Chasers + Invoice Reminders (₹6,999 One-Time or ₹1,499/month)", body)

        # 4. Call to Action
        self.assertIn("No phone call needed! Reply to this email with 'PLAN 1', 'PLAN 2', or 'PLAN 3' to activate this on your inbox in 2 minutes.", body)

    def test_advertise_cli_argument(self):
        """Requirement 5: CLI support for python main.py --advertise <emails>."""
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            cwd=str(Path(__file__).resolve().parent.parent)
        )
        self.assertEqual(result.returncode, 0)
        out_text = result.stdout or ""
        self.assertIn("--advertise", out_text)
        self.assertIn("SmartCal Systems", out_text)
        self.assertNotIn("Antigravity", out_text)

    def test_plan_selection_detection(self):
        """Test NLP detection of PLAN 1, PLAN 2, and PLAN 3."""
        extractor = EmailEntityExtractor(default_tz="IST")

        # Plan 1 detection
        res1 = extractor.extract_all(
            subject="Re: Pricing",
            body_text="I would love to try PLAN 1 please.",
            sender_name="Client One",
            sender_email="client1@example.com"
        )
        self.assertEqual(res1["selected_plan"], "plan_1")
        self.assertEqual(res1["email_type"], "checkout")
        self.assertFalse(res1["is_meeting_request"])

        # Plan 2 detection
        res2 = extractor.extract_all(
            subject="Sign me up",
            body_text="Let's do plan 2 solo inbox setup",
            sender_name="Client Two",
            sender_email="client2@example.com"
        )
        self.assertEqual(res2["selected_plan"], "plan_2")
        self.assertEqual(res2["email_type"], "checkout")
        self.assertFalse(res2["is_meeting_request"])

        # Plan 3 detection
        res3 = extractor.extract_all(
            subject="Agency license",
            body_text="We need PLAN 3 for our 5 inboxes",
            sender_name="Client Three",
            sender_email="client3@example.com"
        )
        self.assertEqual(res3["selected_plan"], "plan_3")
        self.assertEqual(res3["email_type"], "checkout")
        self.assertFalse(res3["is_meeting_request"])

    def test_plan_1_checkout_email(self):
        """Test Plan 1 Free Trial checkout email content and HTML structure."""
        reply = self.drafter.generate_reply({
            "subject": "Trial Inquiry",
            "selected_plan": "plan_1",
            "sender_name": "Test User",
            "sender_email": "user@example.com"
        })
        self.assertIn("SmartCal Systems", reply["subject"])
        self.assertIn("Plan 1", reply["subject"])
        self.assertIn("html_body", reply)

        # Plan 1 Requirements: 3 simple steps to generate 16-letter Gmail App Password
        html = reply["html_body"]
        self.assertIn("myaccount.google.com/apppasswords", html)
        self.assertIn("16-letter", html)
        self.assertIn("SmartCal Systems", html)
        self.assertIn("Plan 1", html)

    def test_plan_2_and_3_software_invoices(self):
        """Test Plan 2 (₹2,999) and Plan 3 (₹6,999) official Software Invoices with QR code."""
        # Plan 2
        reply_p2 = self.drafter.generate_reply({
            "subject": "Upgrading License",
            "selected_plan": "plan_2",
            "sender_name": "Solo Founder",
            "sender_email": "founder@solo.com"
        })
        html_p2 = reply_p2["html_body"]
        self.assertIn("SmartCal Systems Billing Desk", html_p2)
        self.assertIn("Merchant", html_p2)
        self.assertIn("SmartCal Systems (Automated Email &amp; Calendar Cloud)", html_p2)
        self.assertIn("Plan 2 (₹2,999)", html_p2)
        self.assertIn('<img src="https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=upi://pay?pa=7483218482@ibl%26pn=SmartCal%20Systems%26tn=SmartCal%20License%26am=2999%26cu=INR" alt="SmartCal Systems Payment QR" />', html_p2)
        self.assertIn("Billing VPA: 7483218482@ibl (Verified Corporate Signatory Account)", html_p2)
        self.assertIn("Reply to this email with your UPI Reference / UTR Number and your 16-letter App Password to activate your license within 15 minutes.", html_p2)

        # Plan 3
        reply_p3 = self.drafter.generate_reply({
            "subject": "Agency License Upgrade",
            "selected_plan": "plan_3",
            "sender_name": "Agency Principal",
            "sender_email": "agency@pro.com"
        })
        html_p3 = reply_p3["html_body"]
        self.assertIn("SmartCal Systems Billing Desk", html_p3)
        self.assertIn("Plan 3 (₹6,999)", html_p3)
        self.assertIn('<img src="https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=upi://pay?pa=7483218482@ibl%26pn=SmartCal%20Systems%26tn=SmartCal%20License%26am=6999%26cu=INR" alt="SmartCal Systems Payment QR" />', html_p3)
        self.assertIn("Billing VPA: 7483218482@ibl (Verified Corporate Signatory Account)", html_p3)
        self.assertIn("Reply to this email with your UPI Reference / UTR Number and your 16-letter App Password to activate your license within 15 minutes.", html_p3)

    def test_privacy_no_personal_name_or_phone_number(self):
        """Rule: Never display any personal name or phone number anywhere in checkout emails."""
        for plan in ["plan_1", "plan_2", "plan_3"]:
            reply = self.drafter.generate_reply({
                "subject": "License",
                "selected_plan": plan,
                "sender_name": "Alexander Hamilton",
                "sender_email": "alexander@treasury.gov"
            })
            combined_text = reply["body"] + " " + reply.get("html_body", "")

            # Verify no personal name is rendered
            self.assertNotIn("Alexander", combined_text)
            self.assertNotIn("Hamilton", combined_text)

            # Verify no personal phone numbers (e.g. +91, 10-digit mobile numbers)
            import re
            # Match standard telephone patterns like +91 98..., (555)..., 10 digit phone numbers with standard phone prefix
            phone_matches = re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", combined_text)
            # The only numeric sequence is the VPA 7483218482@ibl inside the UPI URL or VPA string
            for match in phone_matches:
                self.assertIn("7483218482", match)  # Corporate VPA account only

    def test_ist_timezone_used_everywhere(self):
        """Rule: Display all scheduled times in 'IST' instead of 'UTC'."""
        now = datetime.utcnow()
        meet_dt = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)

        # 1. Test Email Drafter meeting confirmation
        draft = self.drafter.generate_reply({
            "subject": "Sync Call",
            "is_meeting_request": True,
            "proposed_datetime": meet_dt,
            "duration_minutes": 45,
            "sender_name": "Alice Smith"
        })
        self.assertIn("IST", draft["body"])
        self.assertNotIn("UTC", draft["body"])

        # 2. Test Email Drafter inquiry slot
        draft_inquiry = self.drafter.generate_reply({
            "subject": "Questions",
            "email_type": "inquiry",
            "sender_name": "Alice Smith"
        })
        self.assertIn("IST", draft_inquiry["body"])
        self.assertNotIn("UTC", draft_inquiry["body"])

        # 3. Test UnifiedCalendarScheduler alternative slots
        connector = MockEcosystemConnector(ecosystem="google")
        scheduler = UnifiedCalendarScheduler(connector)
        slots = scheduler.find_alternative_slots(meet_dt, count=3)
        self.assertTrue(len(slots) > 0)
        for s in slots:
            self.assertIn("IST", s["formatted"])
            self.assertNotIn("UTC", s["formatted"])

    def test_duplicate_prevention_and_single_smtp_send(self):
        """Rule: Send SMTP email reply only ONCE per unread message and mark as read immediately."""
        manager = AutomationWorkflowManager(force_simulation=True)
        # Clear mock sent emails before test
        for entry in manager.account_connectors.values():
            connector = entry["connector"]
            if hasattr(connector, "_sent_emails"):
                connector._sent_emails.clear()

        # Run pipeline on multi-account mock
        summary = manager.process_all_ecosystems()

        # Check each connector: count sent emails
        total_unread_scanned = summary["emails_scanned"]
        total_sent = 0
        for entry in manager.account_connectors.values():
            connector = entry["connector"]
            if hasattr(connector, "_sent_emails"):
                total_sent += len(connector._sent_emails)

        # Exactly 1 sent email per processed email
        self.assertEqual(total_sent, summary["emails_processed"])

    def test_remove_attendees_and_format_calendar_title(self):
        """Rule 1: Remove Attendees section from calendar confirmation emails and format meeting title."""
        now = datetime.utcnow()
        meet_dt = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)

        # 1. Email Drafter Meeting Confirmation
        reply = self.drafter.generate_reply({
            "subject": "Demo Request",
            "is_meeting_request": True,
            "proposed_datetime": meet_dt,
            "duration_minutes": 45,
            "sender_name": "Marcus Aurelius",
            "attendees": ["marcus@rome.gov", "senate@rome.gov"]
        })

        self.assertEqual(reply["subject"], "Calendar Invitation: SmartCal Systems Live Demo & Consultation")
        body = reply["body"]
        self.assertNotIn("Attendees:", body)
        self.assertNotIn("marcus@rome.gov", body)
        self.assertNotIn("senate@rome.gov", body)
        self.assertNotIn("Marcus", body)
        self.assertIn("Hello,", body)

        # 2. Google Workspace Connector Calendar Event
        google_conn = GoogleWorkspaceConnector(
            credentials={"email": "smartcal.systems@gmail.com", "app_password": "dummy"},
            settings={"google": {}}
        )
        event = google_conn.create_calendar_event(
            title="Old Title",
            start_time=meet_dt,
            end_time=meet_dt + timedelta(minutes=45),
            attendees=["client@corp.com", "mm5921448@gmail.com"],
            description="Scheduled autonomously by SmartCal Systems Automation Agent.\nAttendees:\n- client@corp.com\n- mm5921448@gmail.com"
        )
        self.assertEqual(event.title, "Calendar Invitation: SmartCal Systems Live Demo & Consultation")
        self.assertNotIn("Attendees:", event.description)
        self.assertNotIn("client@corp.com", event.description)
        self.assertNotIn("mm5921448@gmail.com", event.attendees)

    def test_force_sender_display_name_smartcal_systems(self):
        """Rule 2: Force From header strictly to 'SmartCal Systems <smartcal.systems@gmail.com>'."""
        from unittest.mock import patch, MagicMock

        google_conn = GoogleWorkspaceConnector(
            credentials={"email": "different_sender@gmail.com", "app_password": "dummypassword"},
            settings={"google": {}}
        )

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server

            # Test send_email plain text
            success = google_conn.send_email(
                recipient="client@test.com",
                subject="Test Subject",
                body="Test Body"
            )
            self.assertTrue(success)
            send_args = mock_server.sendmail.call_args[0]
            raw_msg = send_args[2]
            self.assertIn("From: SmartCal Systems <smartcal.systems@gmail.com>", raw_msg)

            # Test send_email HTML
            success_html = google_conn.send_email(
                recipient="client@test.com",
                subject="Test HTML Subject",
                body="Test Plain Body",
                html_body="<p>Test HTML Body</p>"
            )
            self.assertTrue(success_html)
            send_args_html = mock_server.sendmail.call_args[0]
            raw_msg_html = send_args_html[2]
            self.assertIn("From: SmartCal Systems <smartcal.systems@gmail.com>", raw_msg_html)

    def test_block_personal_email_references(self):
        """Rule 3: Ensure mm5921448@gmail.com is strictly blocked and never included anywhere."""
        from connectors.google_connector import is_system_or_noreply
        import json

        # Blocked sender check
        self.assertTrue(is_system_or_noreply("mm5921448@gmail.com", "Hello"))
        self.assertTrue(is_system_or_noreply("MM5921448@GMAIL.COM", "Important question"))

        # Attendee extraction filter
        extractor = EmailEntityExtractor()
        attendees = extractor.extract_attendees("Meeting with mm5921448@gmail.com and client@corp.com", "mm5921448@gmail.com")
        self.assertNotIn("mm5921448@gmail.com", attendees)
        self.assertIn("client@corp.com", attendees)

        # Config check
        with open("config/credentials.json", "r", encoding="utf-8") as f:
            creds_raw = f.read()
        self.assertNotIn("mm5921448@gmail.com", creds_raw)


    def test_compliance_intent_detection(self):
        """Compliance: NLP correctly detects STOP/DELETE/REVOKE/UNSUBSCRIBE and I AGREE."""
        extractor = EmailEntityExtractor()

        # Kill-switch inputs
        for kw in ["STOP", "unsubscribe", "REVOKE", "Please delete my account"]:
            res = extractor.extract_all(subject="Important", body_text=kw, sender_name="User", sender_email="user@test.com")
            self.assertEqual(res.get("compliance_intent"), "revoke_and_delete")
            self.assertEqual(res.get("email_type"), "compliance_revoke")
            self.assertFalse(res.get("is_meeting_request"))

        # Explicit consent inputs
        for kw in ["I AGREE", "agree to terms", "accept terms", "I consent to processing"]:
            res = extractor.extract_all(subject="Re: Terms", body_text=kw, sender_name="User", sender_email="user@test.com")
            self.assertEqual(res.get("compliance_intent"), "consent_agree")
            self.assertEqual(res.get("email_type"), "compliance_consent")
            self.assertFalse(res.get("is_meeting_request"))

    def test_consent_log_archive_and_suppression(self):
        """Compliance 1: Consent log archiving in config/consent_log.json with IST timestamp."""
        test_email = "client.compliance@testcorp.in"
        consent_text = "I AGREE - Terms Accepted via web portal"
        
        entry = self.vault.log_consent(email=test_email, consent_text=consent_text, status="AUTHORIZED")
        self.assertEqual(entry["email"], test_email)
        self.assertEqual(entry["status"], "AUTHORIZED")
        self.assertIn("IST", entry["timestamp_ist"])
        self.assertTrue(self.vault.has_active_consent(test_email))

        # Check suppression
        self.assertFalse(self.vault.is_unsubscribed(test_email))
        self.vault.add_to_unsubscribed(test_email)
        self.assertTrue(self.vault.is_unsubscribed(test_email))

    def test_kill_switch_and_revocation_wipe(self):
        """Compliance 3: Instant STOP/DELETE kill-switch wipes credentials, updates consent, and confirms."""
        test_email = "killswitch.user@enterprise.org"
        
        # Add account to vault first
        self.vault.add_simple_account(email=test_email, password="password123", auto_send=False)
        accounts_before = [a for a in self.vault.list_accounts() if a.get("email") == test_email]
        self.assertEqual(len(accounts_before), 1)

        # Log initial consent
        self.vault.log_consent(email=test_email, consent_text="Initial agreement", status="AUTHORIZED")
        self.assertTrue(self.vault.has_active_consent(test_email))

        # Execute kill-switch
        deleted = self.vault.delete_account_by_email(test_email)
        self.assertTrue(deleted)
        accounts_after = [a for a in self.vault.list_accounts() if a.get("email") == test_email]
        self.assertEqual(len(accounts_after), 0)

        self.vault.add_to_unsubscribed(test_email)
        self.assertTrue(self.vault.is_unsubscribed(test_email))

        self.vault.update_consent_status(test_email, status="REVOKED_AND_WIPED")
        self.assertFalse(self.vault.has_active_consent(test_email))

        # Check deletion email text
        del_email = self.drafter.generate_dpdp_deletion_email("Delete My Data")
        self.assertIn("permanently deleted from SmartCal Systems in compliance with the Indian DPDP Act, 2023", del_email["body"])

    def test_zero_private_data_retention_in_audit_log(self):
        """Compliance 2: Ensure audit log stores ONLY non-sensitive metadata and ZERO body text."""
        from pipeline.audit_logger import AuditLogger
        import tempfile
        import json
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = Path(tf.name)

        try:
            logger = AuditLogger(log_path=temp_path)
            # Attempt to log sensitive record with body snippets
            sensitive_record = {
                "account_label": "Google Workspace (test)",
                "sender": "secret.client@private.com",
                "subject": "Confidential Merger Details",
                "action_items": ["Private NDA negotiation text", "Secret financial projections"],
                "draft_preview": "Hi Client,\nConfidential text of internal business email...",
                "body_text": "Highly private raw email body contents",
                "urgency": "high",
                "meeting_time": "2026-10-01T15:00:00",
                "event_scheduled": True,
                "has_conflict": False
            }
            logger.log_workflow_execution(sensitive_record)

            # Inspect written file
            with open(temp_path, "r", encoding="utf-8") as f:
                audit_content = json.load(f)

            saved_rec = audit_content["records"][0]
            self.assertEqual(saved_rec["account_label"], "Google Workspace (test)")
            self.assertEqual(saved_rec["urgency"], "high")
            self.assertEqual(saved_rec["meeting_time"], "2026-10-01T15:00:00")
            
            # Zero body retention assertions
            self.assertNotIn("draft_preview", saved_rec)
            self.assertNotIn("action_items", saved_rec)
            self.assertNotIn("body_text", saved_rec)
            self.assertNotIn("Confidential Merger Details", str(saved_rec))
            self.assertNotIn("Private NDA negotiation text", str(saved_rec))
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_ironclad_legal_notice_in_all_emails(self):
        """Compliance 4: Legal notice footer present in every automated draft and invoice."""
        from engine.email_drafter import LEGAL_NOTICE_FOOTER
        
        # Required phrases
        self.assertIn("Authorization (IT Act, 2000 & DPDP Act, 2023)", LEGAL_NOTICE_FOOTER)
        self.assertIn("Instant Revocation", LEGAL_NOTICE_FOOTER)
        self.assertIn("'AS-IS' Software & Uptime Notice", LEGAL_NOTICE_FOOTER)
        self.assertIn("Bengaluru, Karnataka under the Arbitration and Conciliation Act, 1996", LEGAL_NOTICE_FOOTER)
        self.assertIn("Reply 'STOP' at any time to opt out of all messages.", LEGAL_NOTICE_FOOTER)

        # 1. Standard reply
        rep = self.drafter.generate_reply({
            "subject": "Meeting sync",
            "sender_name": "Rohan",
            "is_meeting_request": False,
            "action_items": []
        })
        self.assertIn(LEGAL_NOTICE_FOOTER, rep["body"])

        # 2. Followup chaser
        chaser = self.drafter.generate_followup_chaser("Project Alpha", "Rohan")
        self.assertIn(LEGAL_NOTICE_FOOTER, chaser["body"])

        # 3. MoM email
        mom = self.drafter.generate_mom_email("Architecture Review", ["rohan@test.com"], {"summary": "Reviewed arch"})
        self.assertIn(LEGAL_NOTICE_FOOTER, mom["body"])

        # 4. No-show recovery
        noshow = self.drafter.generate_noshow_recovery_email("Client Sync", "Rohan", "rohan@test.com", [])
        self.assertIn(LEGAL_NOTICE_FOOTER, noshow["body"])

        # 5. Role handoff
        handoff = self.drafter.generate_role_handoff_draft("Support Query", "Rohan", "ops@test.com")
        self.assertIn(LEGAL_NOTICE_FOOTER, handoff["body"])

        # 6. Checkout emails
        for plan in ["plan_1", "plan_2", "plan_3"]:
            checkout = self.drafter.generate_checkout_email(plan, "My Plan")
            self.assertIn(LEGAL_NOTICE_FOOTER, checkout["body"])
            self.assertIn("LEGAL TERMS, PRIVACY &amp; LIABILITY NOTICE", checkout["html_body"])


if __name__ == "__main__":
    unittest.main()







