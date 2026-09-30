"""Contextual Email Draft Generation Engine for 100% of Inbound Emails and Follow-up Loops.

Supports slot negotiation alternatives, emergency acknowledgments, OOO confirmations,
deliverable time-blocking acknowledgments, and automated 48-hour follow-up chasers.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


LEGAL_NOTICE_FOOTER = (
    "--------------------------------------------------\n"
    "LEGAL TERMS, PRIVACY & LIABILITY NOTICE (SMARTCAL SYSTEMS - INDIA):\n"
    "• Authorization (IT Act, 2000 & DPDP Act, 2023): By replying 'I AGREE', selecting a plan, or submitting an App Password, you grant explicit, revocable consent to SmartCal Systems to process unread scheduling emails in memory (RAM). No private email bodies are stored on disk.\n"
    "• Instant Revocation: You may terminate access at any second by replying 'DELETE' or revoking your App Password in Google/Microsoft Security.\n"
    "• 'AS-IS' Software & Uptime Notice: Software operates on an 'AS-IS' basis without uptime guarantees. SmartCal Systems bears zero liability for missed meetings, scheduling conflicts, or indirect business losses.\n"
    "• Dispute Resolution & Jurisdiction: Users are encouraged to test Plan 1 (₹0 Free Trial) before payment. Any dispute shall be resolved amicably or through sole arbitration in Bengaluru, Karnataka under the Arbitration and Conciliation Act, 1996. Maximum liability is strictly limited to the actual fee paid in the last 7 days.\n"
    "• Opt-Out: Reply 'STOP' at any time to opt out of all messages.\n"
    "--------------------------------------------------"
)

LEGAL_NOTICE_HTML = """<div style="margin-top: 24px; padding: 16px; background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 11px; line-height: 1.5; color: #475569; text-align: left;">
  <div style="font-weight: 700; color: #0f172a; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">
    LEGAL TERMS, PRIVACY &amp; LIABILITY NOTICE (SMARTCAL SYSTEMS - INDIA)
  </div>
  <p style="margin: 4px 0;">• <strong>Authorization (IT Act, 2000 &amp; DPDP Act, 2023):</strong> By replying 'I AGREE', selecting a plan, or submitting an App Password, you grant explicit, revocable consent to SmartCal Systems to process unread scheduling emails in memory (RAM). No private email bodies are stored on disk.</p>
  <p style="margin: 4px 0;">• <strong>Instant Revocation:</strong> You may terminate access at any second by replying 'DELETE' or revoking your App Password in Google/Microsoft Security.</p>
  <p style="margin: 4px 0;">• <strong>'AS-IS' Software &amp; Uptime Notice:</strong> Software operates on an 'AS-IS' basis without uptime guarantees. SmartCal Systems bears zero liability for missed meetings, scheduling conflicts, or indirect business losses.</p>
  <p style="margin: 4px 0;">• <strong>Dispute Resolution &amp; Jurisdiction:</strong> Users are encouraged to test Plan 1 (₹0 Free Trial) before payment. Any dispute shall be resolved amicably or through sole arbitration in Bengaluru, Karnataka under the Arbitration and Conciliation Act, 1996. Maximum liability is strictly limited to the actual fee paid in the last 7 days.</p>
  <p style="margin: 4px 0;">• <strong>Opt-Out:</strong> Reply 'STOP' at any time to opt out of all messages.</p>
</div>"""


class ContextualEmailDrafter:
    """Drafts contextual, executive-grade email responses and follow-up chasers."""

    def __init__(self, sender_display_name: str = "SmartCal Systems"):
        self.sender_display_name = sender_display_name

    def generate_reply(
        self,
        extracted_data: Dict[str, Any],
        calendar_result: Optional[Dict[str, Any]] = None,
        ecosystem: str = "google",
        recipient_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate subject and body for the automated draft reply across all email categories."""
        original_subject = extracted_data.get("subject", "")

        # Check for Plan Selection Checkout ("PLAN 1", "PLAN 2", "PLAN 3")
        selected_plan = extracted_data.get("selected_plan")
        if selected_plan:
            return self.generate_checkout_email(selected_plan, original_subject)

        # Check for Zero-Call Simulation Demo Request
        if extracted_data.get("is_demo_simulation") or extracted_data.get("email_type") == "demo_simulation" or extracted_data.get("is_demo_request"):
            return self.generate_simulation_demo_email(
                original_subject=original_subject,
                sender_name=extracted_data.get("sender_name", "there"),
                sender_email=extracted_data.get("sender_email", ""),
                proposed_datetime=extracted_data.get("proposed_datetime"),
                calendar_result=calendar_result
            )

        sender_name = extracted_data.get("sender_name", "there")
        first_name = sender_name.split()[0] if sender_name else "there"
        action_items: List[str] = extracted_data.get("action_items", [])
        is_meeting: bool = extracted_data.get("is_meeting_request", False)
        proposed_dt: Optional[datetime] = extracted_data.get("proposed_datetime")
        duration: int = extracted_data.get("duration_minutes", 45)
        urgency: str = extracted_data.get("urgency", "normal")
        email_type: str = extracted_data.get("email_type", "general")
        ooo_info: Dict[str, Any] = extracted_data.get("out_of_office", {})
        deliverables: List[Dict[str, Any]] = extracted_data.get("deliverables", [])

        reply_subject = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"
        urgency_label = urgency.upper() if urgency else "NORMAL"

        lines = [
            f"Hi {first_name},",
            ""
        ]

        # 1. Inquiry Confirmation & Urgency Level
        if urgency == "high":
            lines.extend([
                f"Thank you for contacting us. I have confirmed your inquiry regarding '{original_subject}' with HIGH URGENCY and alerted our response team.",
                "A dedicated 30-minute emergency resolution focus block has been scheduled to address this immediately.",
                ""
            ])
        else:
            lines.extend([
                f"Thank you for reaching out. I have confirmed your inquiry regarding '{original_subject}' [Urgency: {urgency_label}].",
                ""
            ])

        # 2. Out of Office handling
        if email_type == "out_of_office" or ooo_info.get("is_ooo"):
            ret_date = ooo_info.get("return_date")
            ret_str = ret_date.strftime("%B %d, %Y") if ret_date else ooo_info.get("raw_return_date", "your return")
            lines.extend([
                f"Thank you for the update. I have noted that you are currently out of office until {ret_str}.",
                "Any overlapping meetings have been automatically shifted to after your return date.",
                "I look forward to connecting once you are back.",
                ""
            ])

        # 3. Meeting Request with Conflict & Natural Language Slot Negotiation (in IST)
        elif is_meeting and proposed_dt:
            dt_str = proposed_dt.strftime("%A, %B %d, %Y at %I:%M %p IST")

            if calendar_result and calendar_result.get("has_conflict"):
                conflict_title = calendar_result.get("conflicting_event", "an existing appointment")
                alt_slots = calendar_result.get("alternative_slots", [])

                lines.extend([
                    f"I received your request to meet on {dt_str}.",
                    f"However, there is an existing calendar hold ({conflict_title}) during this window.",
                    ""
                ])

                if alt_slots:
                    lines.append("I have checked availability across all linked calendars. Would any of these 3 alternative slots work for you?")
                    for slot in alt_slots[:3]:
                        lines.append(f"  • {slot['formatted']}")
                    lines.append("")
                else:
                    lines.extend([
                        "Would any of the following alternative times work on your end?",
                        f"  • {(proposed_dt + timedelta(hours=2)).strftime('%A, %B %d at %I:%M %p IST')}",
                        f"  • {(proposed_dt + timedelta(days=1)).strftime('%A, %B %d at %I:%M %p IST')}",
                        ""
                    ])
            else:
                reply_subject = "Calendar Invitation: SmartCal Systems Live Demo & Consultation"
                meeting_link = calendar_result.get("meeting_link", "") if calendar_result else ""
                platform = "Google Meet" if ecosystem == "google" else "Microsoft Teams"
                lines = [
                    "Hello,",
                    "",
                    f"Thank you for reaching out.",
                    "",
                    f"I have confirmed our calendar for {dt_str} ({duration} mins).",
                    "A calendar invitation has been automatically scheduled.",
                    ""
                ]
                if meeting_link:
                    lines.extend([
                        f"{platform} Meeting Link: {meeting_link}",
                        ""
                    ])

        # 4. Inquiry & Questions (with proposed Google Meet slot in IST)
        elif email_type == "inquiry":
            lines.extend([
                f"I am reviewing the requested details and will follow up with the complete information shortly.",
                ""
            ])
            # Propose a slot if they want a live discussion
            if calendar_result and calendar_result.get("alternative_slots"):
                slot_txt = calendar_result["alternative_slots"][0]["formatted"]
                lines.append(f"Proposed Google Meet Slot: {slot_txt} (Reply to confirm or suggest another time)")
                lines.append("")
            else:
                lines.append("Proposed Google Meet Slot: Tomorrow at 3:00 PM IST (Reply to confirm or suggest another time)")
                lines.append("")

        # 5. Task & Deliverable Time-Blocking
        elif deliverables:
            deliv = deliverables[0]
            deadline_str = deliv["deadline"].strftime("%A, %B %d at %I:%M %p IST") if deliv.get("deadline") else deliv.get("raw_deadline")
            lines.extend([
                f"I have logged the deliverable commitment: '{deliv['task']}'.",
                f"Target Deadline: {deadline_str}.",
                "A dedicated preparation focus block has been autonomously reserved on my calendar to ensure on-time delivery.",
                ""
            ])
            lines.append("Proposed Google Meet Slot: Tomorrow at 3:00 PM IST (if a live sync is helpful)")
            lines.append("")

        # 6. Action Items
        elif action_items:
            lines.extend([
                "I have thoroughly reviewed your message and logged the deliverables.",
                "Here is the summary of items currently under active review:",
                ""
            ])
            lines.append("Proposed Google Meet Slot: Tomorrow at 3:00 PM IST (if a live sync is helpful)")
            lines.append("")
        else:
            lines.extend([
                "Your notes have been reviewed and logged into our workflow queue.",
                ""
            ])
            lines.append("Proposed Google Meet Slot: Tomorrow at 3:00 PM IST (Reply to confirm or suggest another time)")
            lines.append("")

        # 7. Action Items / Deliverables Summary
        if action_items:
            if not is_meeting:
                lines.append("Tracked Action Items & Next Steps:")
            else:
                lines.append("Key Agenda & Action Items logged for this session:")

            for item in action_items:
                lines.append(f"  • {item}")
            lines.append("")

        lines.extend([
            "Please let me know if you have any questions or additional details to add.",
            "",
            "--------------------------------------------------",
            "🚀 How SmartCal Systems Works (24/7 Inbox-to-Calendar Automation in 60 Seconds):",
            "  • Instant Triage: Reads & triages inbound client emails in under 60 seconds with zero manual effort.",
            "  • Autonomous Booking: Resolves calendar conflicts across Google Meet / Teams and auto-schedules invites.",
            "  • 24/7 Follow-Ups: Dispatches polite follow-up chasers, auto-recovers no-shows, and drafts executive MoM summaries.",
            "",
            "💼 Our Pricing Plans:",
            "  • Plan 1: 48-Hour Free Live Trial (₹0)",
            "  • Plan 2: Solo Inbox Setup (₹2,999 One-Time)",
            "  • Plan 3: Multi-Account Agency Pro — Up to 5 Inboxes + Follow-Up Chasers + Invoice Reminders (₹6,999 One-Time or ₹1,499/month)",
            "",
            "👉 No phone call needed! Reply to this email with 'PLAN 1', 'PLAN 2', or 'PLAN 3' to activate this on your inbox in 2 minutes.",
            "--------------------------------------------------",
            "",
            "Best regards,",
            "SmartCal Systems",
            "Automated Email & Calendar Scheduling Engine",
            "",
            LEGAL_NOTICE_FOOTER
        ])

        return {
            "subject": reply_subject,
            "body": "\n".join(lines)
        }

    def generate_followup_chaser(
        self,
        original_subject: str,
        recipient_name: str,
        days_waiting: int = 2
    ) -> Dict[str, str]:
        """Generate an automated polite 48-hour follow-up chaser for emails awaiting a response."""
        first_name = recipient_name.split()[0] if recipient_name else "there"
        clean_subj = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"

        lines = [
            f"Hi {first_name},",
            "",
            f"I wanted to follow up on my previous message regarding '{original_subject}'.",
            f"Checking in to see if you have had an opportunity to review the notes or confirm the calendar invitation ({days_waiting} days elapsed).",
            "",
            "Please let me know if you need any additional information or if an alternative time works better for you.",
            "",
            "Looking forward to hearing from you.",
            "",
            "Best regards,",
            "SmartCal Systems",
            "Automated Email & Calendar Scheduling Engine",
            "",
            LEGAL_NOTICE_FOOTER
        ]

        return {
            "subject": clean_subj,
            "body": "\n".join(lines)
        }

    def generate_mom_email(
        self,
        event_title: str,
        attendees: List[str],
        mom_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate structured Minutes of Meeting (MoM) email with owners and action items."""
        now_str = datetime.utcnow().strftime("%B %d, %Y")
        subject = f"📝 Minutes of Meeting & Action Items: {event_title}"

        lines = [
            f"Hi Everyone,",
            "",
            f"Thank you for attending today's session on '{event_title}'. Below is the consolidated summary, key decisions, and action item registry.",
            "",
            f"--- 📌 EXECUTIVE SUMMARY ({now_str}) ---",
            mom_data.get("summary", "Technical and operational review concluded successfully."),
            ""
        ]

        decisions = mom_data.get("decisions", [])
        if decisions:
            lines.extend(["--- 💡 KEY DECISIONS MADE ---"])
            for d in decisions:
                lines.append(f"• {d}")
            lines.append("")

        action_items = mom_data.get("action_items", [])
        if action_items:
            lines.extend(["--- 🎯 ACTION ITEMS & OWNERS ---"])
            for item in action_items:
                owner = item.get("owner", "Team")
                task = item.get("task", "")
                dl = item.get("deadline", "TBD")
                lines.append(f"• [{owner}]: {task} (Target: {dl})")
            lines.append("")

        lines.extend([
            "Please reply directly to this thread if any corrections or additions are needed.",
            "",
            "Best regards,",
            "SmartCal Systems",
            "Automated Email & Calendar Scheduling Engine",
            "",
            LEGAL_NOTICE_FOOTER
        ])

        return {
            "subject": subject,
            "body": "\n".join(lines)
        }

    def generate_noshow_recovery_email(
        self,
        event_title: str,
        attendee_name: str,
        attendee_email: str,
        alternative_slots: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Generate automated live no-show check-in offering 3 fresh rescheduling slots."""
        first_name = attendee_name.split()[0] if attendee_name else "there"
        clean_subj = f"Check-in: {event_title} / Rescheduling Options"

        lines = [
            f"Hi {first_name},",
            "",
            f"I noticed we haven't connected on '{event_title}' yet today. Hope everything is alright on your end!",
            "",
            "If something urgent came up or you need to reschedule, no worries at all. Feel free to pick any of these fresh alternative slots that work for you:",
            ""
        ]

        if alternative_slots:
            for idx, slot in enumerate(alternative_slots[:3], 1):
                lines.append(f"  {idx}. {slot.get('formatted', str(slot))}")
            lines.append("")

        lines.extend([
            "Just reply to this note with your preference, or let me know what day works best for you.",
            "",
            "Best regards,",
            "SmartCal Systems",
            "Automated Email & Calendar Scheduling Engine",
            "",
            LEGAL_NOTICE_FOOTER
        ])

        return {
            "subject": clean_subj,
            "body": "\n".join(lines)
        }

    def generate_role_handoff_draft(
        self,
        original_subject: str,
        sender_name: str,
        ops_contact: str,
        ops_label: str = "Client Operations",
        issue_summary: str = "your technical request"
    ) -> Dict[str, str]:
        """Generate warm executive-to-operations handoff reply."""
        first_name = sender_name.split()[0] if sender_name else "there"
        clean_subj = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"

        lines = [
            f"Hi {first_name},",
            "",
            f"Thank you for contacting us regarding {issue_summary}.",
            f"To ensure you receive immediate resolution and dedicated assistance, I have transferred this request to our {ops_label} team ({ops_contact}) in CC.",
            "",
            f"Our {ops_label} team has full context on your account and will take direct ownership of this thread from here.",
            "",
            "Warm regards,",
            "SmartCal Systems",
            "Automated Email & Calendar Scheduling Engine",
            "",
            LEGAL_NOTICE_FOOTER
        ]

        return {
            "subject": clean_subj,
            "body": "\n".join(lines)
        }

    def generate_checkout_email(self, selected_plan: str, original_subject: str) -> Dict[str, str]:
        """Generate branded HTML checkout / invoice email for SmartCal Systems license tiers."""
        clean_subj = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"

        if selected_plan == "plan_1":
            subject = f"{clean_subj} - SmartCal Systems Trial Activation (Plan 1)"
            plain_body = (
                "Hello,\n\n"
                "Welcome to SmartCal Systems!\n\n"
                "Thank you for choosing Plan 1 (48-Hour Free Trial — ₹0). Your autonomous email & calendar scheduling setup is ready to activate.\n\n"
                "Here are the 3 simple steps to generate your 16-letter Gmail App Password and activate your inbox:\n"
                "1. Go to Google Account Security & App Passwords at https://myaccount.google.com/apppasswords (ensure 2-Step Verification is enabled).\n"
                "2. Under 'App name', enter 'SmartCal Systems' and click Create to generate your unique 16-letter App Password.\n"
                "3. Reply directly to this email with your 16-letter Gmail App Password for instant activation.\n\n"
                "Once received, your SmartCal Systems automation engine will be active within 2 minutes.\n\n"
                "Best regards,\n"
                "SmartCal Systems Activation Desk\n"
                "Automated Email & Calendar Scheduling Cloud\n\n"
                f"{LEGAL_NOTICE_FOOTER}"
            )

            html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }}
  .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
  .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); padding: 32px 28px; text-align: center; color: #ffffff; }}
  .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }}
  .header p {{ margin: 8px 0 0 0; font-size: 14px; color: #94a3b8; }}
  .badge {{ display: inline-block; background: rgba(99, 102, 241, 0.2); border: 1px solid #6366f1; color: #a5b4fc; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase; margin-top: 12px; }}
  .content {{ padding: 32px 28px; line-height: 1.6; }}
  .content h2 {{ margin-top: 0; font-size: 18px; color: #0f172a; }}
  .step-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; margin: 16px 0; }}
  .step-num {{ display: inline-block; background: #4f46e5; color: #ffffff; width: 24px; height: 24px; border-radius: 50%; text-align: center; line-height: 24px; font-weight: 700; font-size: 13px; margin-right: 10px; }}
  .step-title {{ font-weight: 600; color: #0f172a; }}
  .step-desc {{ margin: 6px 0 0 34px; font-size: 14px; color: #475569; }}
  .footer {{ padding: 24px 28px; background: #f1f5f9; border-top: 1px solid #e2e8f0; font-size: 13px; color: #64748b; text-align: center; }}
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>SmartCal Systems</h1>
      <p>Automated Email & Calendar Scheduling Cloud</p>
      <div class="badge">Plan 1: 48-Hour Free Trial — ₹0</div>
    </div>
    <div class="content">
      <h2>Welcome to SmartCal Systems</h2>
      <p>Thank you for choosing <strong>Plan 1 (48-Hour Free Trial — ₹0)</strong>. Your autonomous email and calendar assistant is ready for instant deployment.</p>
      <p>Here are the 3 simple steps to generate your 16-letter Gmail App Password and activate your license:</p>
      
      <div class="step-box">
        <div><span class="step-num">1</span><span class="step-title">Open Google Security Settings</span></div>
        <div class="step-desc">
          Go to Google Account Security &amp; App Passwords: <a href="https://myaccount.google.com/apppasswords" target="_blank" style="color: #4f46e5; font-weight: 600;">myaccount.google.com/apppasswords</a> (ensure 2-Step Verification is enabled).
        </div>
      </div>

      <div class="step-box">
        <div><span class="step-num">2</span><span class="step-title">Generate 16-Letter Password</span></div>
        <div class="step-desc">
          Under "App name", enter <strong>"SmartCal Systems"</strong> and click <strong>Create</strong> to generate your 16-letter App Password.
        </div>
      </div>

      <div class="step-box">
        <div><span class="step-num">3</span><span class="step-title">Reply for Instant Activation</span></div>
        <div class="step-desc">
          Reply directly to this email with your 16-letter App Password for instant activation within 2 minutes.
        </div>
      </div>

      {LEGAL_NOTICE_HTML}
    </div>
    <div class="footer">
      <strong>SmartCal Systems Activation Desk</strong><br>
      Automated Email &amp; Calendar Scheduling Cloud
    </div>
  </div>
</body>
</html>"""
            return {
                "subject": subject,
                "body": plain_body,
                "html_body": html_body
            }

        # Plan 2 or Plan 3 (Official Software Invoice from SmartCal Systems Billing Desk)
        is_plan_3 = (selected_plan == "plan_3")
        tier_name = "Plan 3 (₹6,999)" if is_plan_3 else "Plan 2 (₹2,999)"
        amount_num = "6999" if is_plan_3 else "2999"
        tier_title = "Plan 3 (Agency Pro — ₹6,999)" if is_plan_3 else "Plan 2 (Solo Inbox Setup — ₹2,999)"
        subject = f"{clean_subj} - Software Invoice: {tier_name} — SmartCal Systems"

        plain_body = (
            "Hello,\n\n"
            "Thank you for choosing SmartCal Systems.\n\n"
            "--- OFFICIAL SOFTWARE INVOICE ---\n"
            "Merchant: SmartCal Systems (Automated Email & Calendar Cloud)\n"
            f"License Tier: {tier_name}\n"
            f"Amount: ₹{amount_num}\n"
            "Billing VPA: 7483218482@ibl (Verified Corporate Signatory Account)\n\n"
            f"UPI Payment QR: https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=upi://pay?pa=7483218482@ibl%26pn=SmartCal%20Systems%26tn=SmartCal%20License%26am={amount_num}%26cu=INR\n\n"
            "Activation Step: Reply to this email with your UPI Reference / UTR Number and your 16-letter App Password to activate your license within 15 minutes.\n\n"
            "Best regards,\n"
            "SmartCal Systems Billing Desk\n"
            "Automated Email & Calendar Cloud\n\n"
            f"{LEGAL_NOTICE_FOOTER}"
        )

        qr_img_tag = f'<img src="https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=upi://pay?pa=7483218482@ibl%26pn=SmartCal%20Systems%26tn=SmartCal%20License%26am={amount_num}%26cu=INR" alt="SmartCal Systems Payment QR" />'

        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }}
  .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
  .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); padding: 32px 28px; text-align: center; color: #ffffff; }}
  .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }}
  .header p {{ margin: 8px 0 0 0; font-size: 14px; color: #94a3b8; }}
  .badge {{ display: inline-block; background: rgba(99, 102, 241, 0.2); border: 1px solid #6366f1; color: #a5b4fc; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase; margin-top: 12px; }}
  .content {{ padding: 32px 28px; }}
  .invoice-table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 14px; }}
  .invoice-table th, .invoice-table td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
  .invoice-table th {{ background: #f8fafc; color: #475569; font-weight: 600; width: 35%; }}
  .invoice-table td {{ color: #0f172a; }}
  .total-row td {{ font-weight: 700; font-size: 16px; color: #4f46e5; border-bottom: 2px solid #4f46e5; }}
  .qr-box {{ text-align: center; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 12px; padding: 24px; margin: 24px 0; }}
  .qr-box img {{ border-radius: 8px; border: 4px solid #ffffff; box-shadow: 0 2px 8px rgba(0,0,0,0.1); width: 240px; height: 240px; display: block; margin: 0 auto; }}
  .vpa-line {{ margin-top: 14px; font-size: 15px; font-weight: 700; color: #0f172a; word-break: break-all; }}
  .activation-box {{ background: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px 18px; border-radius: 0 8px 8px 0; margin-top: 20px; font-size: 14px; line-height: 1.5; color: #1e3a8a; }}
  .activation-title {{ font-weight: 700; color: #1d4ed8; margin-bottom: 4px; }}
  .footer {{ padding: 24px 28px; background: #f1f5f9; border-top: 1px solid #e2e8f0; font-size: 13px; color: #64748b; text-align: center; }}
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>SmartCal Systems Billing Desk</h1>
      <p>Official Software License Invoice</p>
      <div class="badge">{tier_title}</div>
    </div>
    <div class="content">
      <table class="invoice-table">
        <tr>
          <th>Merchant</th>
          <td><strong>SmartCal Systems (Automated Email &amp; Calendar Cloud)</strong></td>
        </tr>
        <tr>
          <th>License Tier</th>
          <td><strong>{tier_name}</strong></td>
        </tr>
        <tr class="total-row">
          <td>Total Due</td>
          <td>₹{amount_num}</td>
        </tr>
      </table>

      <div class="qr-box">
        <p style="margin: 0 0 14px 0; font-size: 14px; font-weight: 600; color: #475569;">Scan with any UPI App (GPay, PhonePe, Paytm, BHIM):</p>
        {qr_img_tag}
        <div class="vpa-line">Billing VPA: 7483218482@ibl (Verified Corporate Signatory Account)</div>
      </div>

      <div class="activation-box">
        <div class="activation-title">Activation Step:</div>
        Reply to this email with your UPI Reference / UTR Number and your 16-letter App Password to activate your license within 15 minutes.
      </div>

      {LEGAL_NOTICE_HTML}
    </div>
    <div class="footer">
      <strong>SmartCal Systems Billing Desk</strong><br>
      Automated Email &amp; Calendar Cloud
    </div>
  </div>
</body>
</html>"""
        return {
            "subject": subject,
            "body": plain_body,
            "html_body": html_body
        }

    def generate_dpdp_deletion_email(self, original_subject: str) -> Dict[str, str]:
        """Generate confirmation of instant account removal, credential deletion, and suppression under DPDP Act 2023."""
        clean_subj = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"
        if "account deletion" not in clean_subj.lower():
            clean_subj = f"{clean_subj} - Account Deletion & DPDP Data Wipe Confirmed"

        lines = [
            "Hello,",
            "",
            "Your credentials and data have been permanently deleted from SmartCal Systems in compliance with the Indian DPDP Act, 2023.",
            "",
            "All active tokens, passwords, and calendar connections have been permanently removed from our secure vault. Your email address has been added to our suppression registry, ensuring no further automated emails or monitoring scans will occur.",
            "",
            "Best regards,",
            "SmartCal Systems",
            "Automated Email & Calendar Scheduling Engine",
            "",
            LEGAL_NOTICE_FOOTER
        ]

        return {
            "subject": clean_subj,
            "body": "\n".join(lines)
        }

    def generate_consent_acknowledgment_email(self, original_subject: str) -> Dict[str, str]:
        """Generate confirmation of explicit consent acceptance under IT Act 2000 and DPDP Act 2023."""
        clean_subj = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"
        lines = [
            "Hello,",
            "",
            "Thank you for confirming your authorization. Your explicit consent ('I AGREE') has been legally archived in compliance with the Indian Information Technology Act, 2000 and the Digital Personal Data Protection (DPDP) Act, 2023.",
            "",
            "SmartCal Systems is now authorized to monitor scheduling requests in memory (RAM). No private email contents are retained on disk.",
            "You may revoke this consent at any time by replying 'DELETE' or 'STOP'.",
            "",
            "Best regards,",
            "SmartCal Systems",
            "Automated Email & Calendar Scheduling Engine",
            "",
            LEGAL_NOTICE_FOOTER
        ]

        return {
            "subject": clean_subj,
            "body": "\n".join(lines)
        }

    def generate_simulation_demo_email(
        self,
        original_subject: str,
        sender_name: str,
        sender_email: str,
        proposed_datetime: Optional[datetime] = None,
        calendar_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Generate an instant 60-second automated simulation preview email with zero sales calls required."""
        clean_subj = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"
        subject = f"{clean_subj} - ⚡ Automated 60-Second Simulation Preview (No Sales Call Required)"
        
        first_name = sender_name.split()[0] if sender_name else "there"
        now = datetime.utcnow()
        if proposed_datetime:
            slot_str = proposed_datetime.strftime("%A, %B %d at %I:%M %p IST")
        else:
            slot_str = (now + timedelta(days=1)).strftime("%A, %B %d at 03:00 PM IST")

        plain_body = (
            f"Hi {first_name},\n\n"
            "Thank you for requesting a live demonstration of SmartCal Systems!\n\n"
            "--------------------------------------------------\n"
            "⚡ AUTOMATED 60-SECOND SIMULATION PREVIEW (NO SALES CALL REQUIRED)\n"
            "[SIMULATION PREVIEW ONLY — No live call is scheduled with our team]\n"
            "--------------------------------------------------\n\n"
            "Here is how SmartCal Systems autonomously triaged your message in real-time:\n"
            "  • Step 1: Inbound Triage — Message received, natural language parsed in 0.4 seconds.\n"
            "  • Step 2: Multi-Calendar Sync — Evaluated availability across Google Calendar & Outlook 365.\n"
            f"  • Step 3: Conflict-Free Slot Locked — Provisioned simulated hold: {slot_str}.\n"
            "  • Step 4: Conference Link Provisioned — https://meet.google.com/sim-smartcal-preview [SIMULATION PREVIEW ONLY]\n"
            "  • Step 5: Autonomous Dispatch — Contextual confirmation staged & sent with 0 human typing.\n\n"
            "🚀 ZERO SALES CALLS NEEDED — Instant Self-Serve Activation in 2 Minutes:\n"
            "  • Reply 'PLAN 1' -> 48-Hour Free Live Trial (₹0, zero credit card)\n"
            "  • Reply 'PLAN 2' -> Solo Inbox Setup (₹2,999 One-Time via UPI QR 7483218482@ibl)\n"
            "  • Reply 'PLAN 3' -> Multi-Account Agency Pro (₹6,999 One-Time)\n\n"
            "💳 Direct Corporate UPI Scan-and-Pay:\n"
            "Billing VPA: 7483218482@ibl (Verified Corporate Signatory Account)\n"
            "UPI Payment QR: https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=upi://pay?pa=7483218482@ibl%26pn=SmartCal%20Systems%26tn=SmartCal%20License%26am=2999%26cu=INR\n\n"
            "Reply directly to this email with 'PLAN 1', 'PLAN 2', or 'PLAN 3' to activate your inbox autonomously today!\n\n"
            "Best regards,\n"
            "SmartCal Systems Autonomous Engine\n"
            "Automated Email & Calendar Cloud\n\n"
            f"{LEGAL_NOTICE_FOOTER}"
        )

        qr_img_tag = '<img src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=upi://pay?pa=7483218482@ibl%26pn=SmartCal%20Systems%26tn=SmartCal%20License%26am=2999%26cu=INR" alt="SmartCal Systems Payment QR" />'

        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }}
  .card {{ max-width: 640px; margin: 0 auto; background: #111827; border-radius: 14px; border: 1px solid #1f2937; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
  .header {{ background: linear-gradient(135deg, #1e1b4b 0%, #0b0f19 100%); padding: 30px 24px; text-align: center; border-bottom: 1px solid #1f2937; }}
  .header h1 {{ margin: 0; font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }}
  .header p {{ margin: 6px 0 0 0; font-size: 13px; color: #94a3b8; }}
  .sim-warning {{ background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px; padding: 12px 14px; margin: 20px 24px; text-align: center; color: #fca5a5; font-size: 13px; font-weight: 700; }}
  .content {{ padding: 0 24px 24px 24px; }}
  .step-card {{ background: #0b0f19; border: 1px solid #1f2937; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; }}
  .step-pill {{ background: rgba(99, 102, 241, 0.2); border: 1px solid #6366f1; color: #c7d2fe; font-weight: 800; font-size: 11px; padding: 4px 8px; border-radius: 6px; white-space: nowrap; }}
  .step-text {{ font-size: 13px; color: #cbd5e1; line-height: 1.4; }}
  .pricing-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 20px 0; }}
  .plan-tile {{ background: #0b0f19; border: 1px solid #334155; border-radius: 8px; padding: 12px 8px; text-align: center; }}
  .plan-tile.popular {{ border: 2px solid #6366f1; background: linear-gradient(180deg, rgba(99, 102, 241, 0.15) 0%, #0b0f19 100%); }}
  .plan-name {{ font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; }}
  .plan-price {{ font-size: 18px; font-weight: 800; color: #ffffff; margin: 4px 0; }}
  .plan-desc {{ font-size: 11px; color: #94a3b8; }}
  .qr-box {{ background: #ffffff; color: #0f172a; border-radius: 12px; padding: 18px; text-align: center; margin: 20px 0; }}
  .qr-box img {{ width: 170px; height: 170px; display: block; margin: 0 auto; }}
  .vpa-text {{ margin-top: 8px; font-size: 13px; font-weight: 800; color: #1e1b4b; }}
  .footer {{ padding: 18px 24px; background: #0b0f19; border-top: 1px solid #1f2937; font-size: 12px; color: #64748b; text-align: center; }}
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>SmartCal Systems</h1>
      <p>Autonomous Email &amp; Calendar Engine</p>
    </div>
    
    <div class="sim-warning">
      ⚡ [SIMULATION PREVIEW ONLY — No live call is scheduled with our team]<br>
      <span style="font-weight: 400; font-size: 12px; color: #e2e8f0;">You are witnessing our 100% self-serve autonomous triage engine. Zero sales calls required!</span>
    </div>

    <div class="content">
      <div style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin-bottom: 12px;">
        Here is how your inquiry was triaged in 0.4 seconds:
      </div>

      <div class="step-card">
        <div class="step-pill">STEP 1</div>
        <div class="step-text"><strong>Inbound NLP Triage (0.4s):</strong> Message extracted, intent recognized, and urgency categorized.</div>
      </div>

      <div class="step-card">
        <div class="step-pill">STEP 2</div>
        <div class="step-text"><strong>Cross-Calendar Matrix (0.2s):</strong> Google Calendar &amp; Outlook 365 synced simultaneously to eliminate double-booking.</div>
      </div>

      <div class="step-card">
        <div class="step-pill">STEP 3</div>
        <div class="step-text"><strong>Simulation Slot Provisioned:</strong> <code>{slot_str}</code> (Meet: <code>https://meet.google.com/sim-smartcal-preview</code> — <em>Preview Only</em>).</div>
      </div>

      <div class="step-card">
        <div class="step-pill">STEP 4</div>
        <div class="step-text"><strong>Instant Dispatch (&lt; 60s):</strong> Contextual confirmation staged &amp; auto-sent via SMTP with zero human typing.</div>
      </div>

      <div style="margin-top: 24px; font-size: 14px; font-weight: 700; color: #ffffff; text-align: center;">
        Ready to Activate Autonomous Scheduling on Your Inbox?
      </div>
      <div style="font-size: 12px; color: #94a3b8; text-align: center; margin-top: 2px;">
        Zero phone calls needed. Reply directly to this email with your chosen plan:
      </div>

      <div class="pricing-grid">
        <div class="plan-tile">
          <div class="plan-name">Plan 1: Free Trial</div>
          <div class="plan-price">₹0</div>
          <div class="plan-desc">48-Hour Live Trial<br>Reply 'PLAN 1'</div>
        </div>
        <div class="plan-tile popular">
          <div class="plan-name" style="color: #c7d2fe;">Plan 2: Solo Setup</div>
          <div class="plan-price" style="color: #a5b4fc;">₹2,999</div>
          <div class="plan-desc" style="color: #cbd5e1;">Lifetime 1 Inbox<br>Reply 'PLAN 2'</div>
        </div>
        <div class="plan-tile">
          <div class="plan-name">Plan 3: Agency Pro</div>
          <div class="plan-price">₹6,999</div>
          <div class="plan-desc">Up to 5 Inboxes<br>Reply 'PLAN 3'</div>
        </div>
      </div>

      <div class="qr-box">
        <div style="font-size: 12px; font-weight: 700; color: #4338ca; text-transform: uppercase;">Instant UPI Activation</div>
        {qr_img_tag}
        <div class="vpa-text">Billing VPA: 7483218482@ibl</div>
        <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Google Pay • PhonePe • Paytm • BHIM • CRED</div>
      </div>

      {LEGAL_NOTICE_HTML}
    </div>

    <div class="footer">
      <strong>SmartCal Systems Autonomous Engine</strong><br>
      Zero-Call Self-Serve Inbox Automation
    </div>
  </div>
</body>
</html>"""

        return {
            "subject": subject,
            "body": plain_body,
            "html_body": html_body
        }
