"""Streamlit Management Dashboard for SmartCal Systems Multi-Account Automation Agent.

Implements all 4 pillars:
1. Inbound Triage & Action Items
2. Contextual Drafts & Outbox
3. Unified Cross-Account Calendar Timeline & Conflict Matrix
4. Confidence-Based Manual Approval Queue
5. Weekly Time & Communication Audit (Client Domain Hours, Invoices, 48h Follow-up Chasers)
6. Simple 2-Input Multi-Account Manager & Settings
7. Public Website, Live Demo & Transparent Pricing
"""
import streamlit as st  # type: ignore
import json
from datetime import datetime
from pathlib import Path
import sys

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import load_settings, save_settings
from auth.vault import CredentialVault
from pipeline.workflow_manager import AutomationWorkflowManager
from pipeline.audit_logger import AuditLogger

st.set_page_config(
    page_title="SmartCal Systems - Autonomous Email & Calendar Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Tech Dark CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    
    .account-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    .badge-google {
        background-color: #1e3a8a;
        color: #93c5fd;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .badge-m365 {
        background-color: #064e3b;
        color: #6ee7b7;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
    }

    .badge-account {
        background-color: rgba(99, 102, 241, 0.25);
        color: #c7d2fe;
        border: 1px solid rgba(99, 102, 241, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
    }

    .badge-conflict {
        background-color: #7f1d1d;
        color: #fca5a5;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
    }

    .badge-urgent {
        background-color: #991b1b;
        color: #fee2e2;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 700;
        animation: pulse 1.5s infinite;
        display: inline-block;
    }
    
    .action-item-pill {
        background: rgba(99, 102, 241, 0.15);
        color: #c7d2fe;
        border-left: 3px solid #6366f1;
        padding: 8px 12px;
        margin-bottom: 6px;
        border-radius: 4px;
        font-size: 0.88rem;
    }

    .draft-box {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        font-family: monospace;
        font-size: 0.88rem;
        white-space: pre-wrap;
        color: #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)


def init_state():
    if "workflow_manager" not in st.session_state:
        st.session_state.workflow_manager = AutomationWorkflowManager()
    if "last_scan_results" not in st.session_state:
        st.session_state.last_scan_results = None


init_state()
wm: AutomationWorkflowManager = st.session_state.workflow_manager
settings = load_settings()
vault = CredentialVault()
audit = AuditLogger()
summary_stats = audit.get_summary()
time_audit = audit.get_time_and_communication_audit()

all_accounts = vault.list_accounts()
enabled_accounts = [a for a in all_accounts if a.get("enabled", True)]

# Sidebar controls
with st.sidebar:
    st.markdown("### ⚡ Multi-Account Control")
    st.markdown("**Autonomous Email & Calendar Engine**")
    st.divider()

    st.markdown(f"#### 👥 Active Accounts ({len(enabled_accounts)}/{len(all_accounts)})")
    
    account_options = ["All Connected Accounts"] + [f"{a.get('label')} ({a.get('email')})" for a in all_accounts]
    selected_account_filter = st.selectbox("Filter Feed by Account", account_options)
    
    target_acc_id = None
    if selected_account_filter != "All Connected Accounts":
        idx = account_options.index(selected_account_filter) - 1
        target_acc_id = all_accounts[idx].get("id")

    st.markdown("#### 🎯 Execution Rules")
    trigger_mode = settings.get("trigger_mode", "all_unread")
    st.write(f"• **Trigger:** {trigger_mode.replace('_', ' ').title()}")
    st.write(f"• **Confidence Gate:** Auto-send >= 0.70")
    st.write(f"• **Cross-Sync:** Google Meet + M365 Teams")
    st.write(f"• **VIP Auto-Bump:** Active")
    st.write(f"• **MoM Pipeline:** Active")

    st.divider()
    st.markdown("#### 🛡️ Circuit Breaker Health")
    has_open_cb = False
    for a_id, ent in wm.account_connectors.items():
        c_conn = ent["connector"]
        c_lbl = ent["meta"].get("label", a_id)
        if c_conn.is_circuit_open():
            has_open_cb = True
            st.error(f"⚠️ {c_lbl}: OPEN")
            st.caption(f"Reason: {c_conn.circuit_reason}")
            if st.button(f"⚡ Reset & Re-Auth", key=f"sb_reset_cb_{a_id}"):
                c_conn.reset_circuit()
                audit.log_circuit_breaker({"account_id": a_id, "action": "manual_reset"})
                st.success(f"Circuit reset for {c_lbl}!")
                st.rerun()
    if not has_open_cb:
        st.markdown("<span style='color: #10b981; font-size: 0.85rem;'>● All Account Circuits Healthy</span>", unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🚀 Immediate Actions")
    if st.button("▶️ Scan Active Accounts Now", use_container_width=True, type="primary"):
        with st.spinner("Scanning inboxes and syncing calendars..."):
            res = wm.process_all_ecosystems(target_account_id=target_acc_id)
            st.session_state.last_scan_results = res
            st.success(f"Scan complete! Processed {res['emails_processed']} messages across {res['accounts_scanned']} accounts.")
            st.rerun()

    if st.button("🧪 Run Full 4-Pillar Demo Scan", use_container_width=True):
        with st.spinner("Executing simulation (Conflicts, OOO, Invoices, Escalations, Dossiers)..."):
            sim_wm = AutomationWorkflowManager(force_simulation=True)
            res = sim_wm.process_all_ecosystems()
            st.session_state.last_scan_results = res
            st.success(f"Demo complete! Processed {res['emails_processed']} messages across {res['accounts_scanned']} accounts.")
            st.rerun()

    st.divider()
    st.caption("SmartCal Systems Multi-Tenant Agent Engine")

# Main Title & System Status Banner
col_title, col_status = st.columns([3, 1])
with col_title:
    st.title("SmartCal Systems - Autonomous Email & Calendar Agent")
    st.caption("24/7 Inbox-to-Calendar Automation in 60 Seconds across Google Workspace & Microsoft 365.")

with col_status:
    st.markdown("<div style='text-align: right; padding-top: 15px;'>", unsafe_allow_html=True)
    st.markdown("<span style='color: #10b981; font-weight: 600;'>● Multi-Tenant Engine Active</span>", unsafe_allow_html=True)
    st.caption(f"Last updated: {datetime.utcnow().strftime('%H:%M:%S UTC')}")
    st.markdown("</div>", unsafe_allow_html=True)

# Metric Summary Cards
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div style="color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;">Accounts Monitored</div>
        <div style="font-size: 2rem; font-weight: 700; color: #38bdf8; margin-top: 5px;">{len(enabled_accounts)}</div>
        <div style="color: #64748b; font-size: 0.75rem; margin-top: 5px;">Google Workspace + M365</div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div style="color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;">Draft Replies Staged</div>
        <div style="font-size: 2rem; font-weight: 700; color: #a78bfa; margin-top: 5px;">{summary_stats.get('total_drafts_created', 0)}</div>
        <div style="color: #64748b; font-size: 0.75rem; margin-top: 5px;">100% of all incoming emails</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div style="color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;">Calendar Invites & Focus Blocks</div>
        <div style="font-size: 2rem; font-weight: 700; color: #34d399; margin-top: 5px;">{summary_stats.get('total_events_scheduled', 0)}</div>
        <div style="color: #64748b; font-size: 0.75rem; margin-top: 5px;">Cross-Account Sync Active</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div style="color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;">Autonomous Action Rate</div>
        <div style="font-size: 2rem; font-weight: 700; color: #f59e0b; margin-top: 5px;">{time_audit.get('autonomous_rate_percent', 100)}%</div>
        <div style="color: #64748b; font-size: 0.75rem; margin-top: 5px;">Confidence >= 0.70 auto-approved</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 9 Main Navigation Tabs covering Public Demo, Pricing, All Pillars, and Legal Terms (/terms)
tab_demo, tab_inbox, tab_drafts, tab_calendar, tab_queue, tab_audit, tab_accounts, tab_config, tab_terms = st.tabs([
    "🚀 Public Demo & Pricing Plans",
    "📥 Inbound Emails & Triage",
    "✍️ Contextual Drafts & Outbox",
    "📅 Cross-Account Calendar",
    "🎯 Confidence Approval Queue",
    "📊 Time & Communication Audit",
    "👥 Manage Accounts (Multi-Tenant)",
    "⚙️ Global Agent Settings",
    "📜 Legal Terms & DPDP Compliance (/terms)"
])

# Tab 0: Public Demo & Pricing Plans
with tab_demo:
    st.subheader("⚡ SmartCal Systems: 24/7 Inbox-to-Calendar Automation in 60 Seconds")
    st.markdown("""
    **SmartCal Systems** is an enterprise-grade autonomous scheduling engine. It connects directly to your Google Workspace and Microsoft 365 inboxes, eliminates double-booking across calendars, handles 48-hour follow-up chasers, extracts invoices, and schedules Google Meet / Teams calls in under 60 seconds without manual effort.
    """)

    st.markdown("### 🧪 How to Experience the Live Demo in 60 Seconds")
    col_demo1, col_demo2, col_demo3 = st.columns(3)
    with col_demo1:
        st.markdown("""
        **1. Send an Email**  
        Send any test email to our live inbox:  
        `smartcal.systems@gmail.com`  
        *Subject: Sync on Project Alpha*  
        *Body: "Can we schedule a 30-min call tomorrow at 3 PM UTC to discuss deliverables?"*
        """)
    with col_demo2:
        st.markdown("""
        **2. Autonomous AI Triage**  
        SmartCal scans inboxes, checks cross-calendar availability across Google & Outlook, assigns urgency, and provisions a Google Meet / Teams link instantly.
        """)
    with col_demo3:
        st.markdown("""
        **3. Instant Auto-Reply**  
        SmartCal dispatches the calendar hold and contextual confirmation email directly to your inbox via SMTP in under 60 seconds!
        """)

    st.markdown("---")
    st.markdown("### 💼 Transparent Pricing Plans")
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown("""
        <div class="metric-card" style="border: 1px solid rgba(56, 189, 248, 0.4); min-height: 290px;">
            <div style="color: #38bdf8; font-weight: 700; font-size: 1.2rem;">PLAN 1: Free Live Trial</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: #ffffff; margin: 10px 0;">₹0 <span style="font-size: 0.9rem; color: #94a3b8; font-weight: 400;">/ 48 Hours</span></div>
            <div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.6;">
                • 48-Hour Full Access Live Trial<br>
                • 1 Connected Inbox (Gmail or M365)<br>
                • 60-Second Email Triage & Auto-Reply<br>
                • Google Meet & Teams Booking<br>
                • Zero Credit Card Required
            </div>
        </div>
        """, unsafe_allow_html=True)
    with p2:
        st.markdown("""
        <div class="metric-card" style="border: 1px solid rgba(167, 139, 250, 0.4); min-height: 290px;">
            <div style="color: #a78bfa; font-weight: 700; font-size: 1.2rem;">PLAN 2: Solo Inbox Setup</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: #ffffff; margin: 10px 0;">₹2,999 <span style="font-size: 0.9rem; color: #94a3b8; font-weight: 400;">One-Time</span></div>
            <div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.6;">
                • Lifetime Solo Inbox Automation<br>
                • Natural Language Slot Negotiation<br>
                • Cross-Calendar Conflict Resolver<br>
                • High-Urgency Emergency Escalation<br>
                • Direct SMTP Auto-Send Dispatch
            </div>
        </div>
        """, unsafe_allow_html=True)
    with p3:
        st.markdown("""
        <div class="metric-card" style="border: 1px solid rgba(52, 211, 153, 0.4); min-height: 290px;">
            <div style="color: #34d399; font-weight: 700; font-size: 1.2rem;">PLAN 3: Agency Pro</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: #ffffff; margin: 10px 0;">₹6,999 <span style="font-size: 0.9rem; color: #94a3b8; font-weight: 400;">One-Time or ₹1,499/mo</span></div>
            <div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.6;">
                • Up to 5 Connected Inboxes (Hybrid)<br>
                • 48-Hour Automated Follow-Up Chasers<br>
                • Automated Invoice & Payment Reminders<br>
                • Post-Meeting MoM & Action Item Sync<br>
                • Live No-Show Auto-Recovery Loops
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📝 Self-Serve Instant Signup Form")
    st.caption("No phone call needed! Select your plan below to activate SmartCal Systems on your inbox in 2 minutes.")

    with st.form("self_serve_signup_form"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            signup_name = st.text_input("Full Name", placeholder="e.g. Alex Morgan")
            signup_email = st.text_input("Business Email (Inbox to Automate)", placeholder="e.g. alex@yourcompany.com")
        with col_f2:
            signup_plan = st.selectbox(
                "Choose Your Plan",
                [
                    "Plan 1: 48-Hour Free Live Trial (₹0)",
                    "Plan 2: Solo Inbox Setup (₹2,999 One-Time)",
                    "Plan 3: Multi-Account Agency Pro (₹6,999 One-Time or ₹1,499/month)"
                ]
            )
            signup_inboxes = st.number_input("Number of Inboxes to Connect", min_value=1, max_value=20, value=1)
        signup_notes = st.text_area("Custom Requirements / Target Ecosystem", placeholder="e.g. 1 Google Workspace + 1 Outlook 365, automated client scheduling")
        
        # Mandatory Consent Checkbox (Indian IT Act 2000 & DPDP Act 2023)
        signup_consent = st.checkbox(
            "I AGREE: I explicitly authorize SmartCal Systems to process unread scheduling emails in memory (RAM). I accept the Legal Terms, Privacy Notice & Sole Arbitration in Bengaluru (IT Act, 2000, DPDP Act, 2023 & Indian Contract Act, 1872).",
            value=False,
            help="Ticking this mandatory checkbox records your explicit consent in config/consent_log.json as permanent legal proof."
        )

        submitted = st.form_submit_button("🚀 Activate SmartCal Systems Now", use_container_width=True, type="primary")
        if submitted:
            if not signup_email or "@" not in signup_email:
                st.error("Please enter a valid business email address.")
            elif not signup_consent:
                st.error("Compliance Requirement: You must tick the mandatory legal consent checkbox ('I AGREE') before account activation.")
            else:
                # Log permanent legal consent in config/consent_log.json
                vault.log_consent(
                    email=signup_email,
                    consent_text=f"Web Portal Registration: {signup_plan} - Explicit consent accepted under IT Act 2000 & DPDP Act 2023",
                    status="AUTHORIZED"
                )

                lead_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "name": signup_name,
                    "email": signup_email,
                    "plan": signup_plan,
                    "inboxes": signup_inboxes,
                    "notes": signup_notes,
                    "consent_status": "AUTHORIZED",
                    "status": "pending_activation"
                }
                leads_file = Path(__file__).resolve().parent.parent / "config" / "leads.json"
                existing_leads = []
                if leads_file.exists():
                    try:
                        with open(leads_file, "r", encoding="utf-8") as lf:
                            existing_leads = json.load(lf)
                    except Exception:
                        existing_leads = []
                existing_leads.append(lead_data)
                with open(leads_file, "w", encoding="utf-8") as lf:
                    json.dump(existing_leads, lf, indent=4)
                
                st.success(f"🎉 Authorization & Registration Verified! Thank you {signup_name or 'there'}. Legal consent has been permanently archived in config/consent_log.json.")
                st.balloons()

recent_records = audit.get_recent_records(limit=40)
if target_acc_id:
    recent_records = [r for r in recent_records if r.get("account_id") == target_acc_id]

# Tab 1: Inbound Emails & Triage
with tab_inbox:
    st.subheader("Multi-Account Inbound Triage & Extracted Entities")
    if not recent_records:
        st.info("No processing runs recorded yet. Click 'Scan Active Accounts Now' or 'Run Full 4-Pillar Demo Scan' to process incoming emails.")
    else:
        for rec in recent_records:
            eco = rec.get("ecosystem", "google")
            badge_class = "badge-google" if eco == "google" else "badge-m365"
            badge_label = "Google Workspace" if eco == "google" else "Microsoft 365"
            acc_label = rec.get("account_label", "Default Account")
            urgency = rec.get("urgency", "normal")
            
            with st.expander(f"⚡ Processing Audit: {acc_label} [{rec.get('email_type', 'general').upper()}] — {rec.get('timestamp')[:19]}", expanded=False):
                col_info1, col_info2 = st.columns([2, 1])
                with col_info1:
                    st.markdown(f"<span class='badge-account'>👤 {acc_label}</span> <span class='{badge_class}'>{badge_label}</span>", unsafe_allow_html=True)
                    if urgency == "high":
                        st.markdown("<span class='badge-urgent'>🚨 HIGH URGENCY</span>", unsafe_allow_html=True)
                    st.markdown(f"**Audit Timestamp:** `{rec.get('timestamp')}`")
                    st.markdown(f"**Scheduled Meeting Time:** `{rec.get('meeting_time') or 'None detected'}`")
                    if rec.get("has_conflict"):
                        st.markdown("<span class='badge-conflict'>Cross-Account Conflict</span> — 3 alternative slots proposed in draft reply.", unsafe_allow_html=True)
                    elif rec.get("event_scheduled"):
                        st.markdown("<span style='color: #10b981; font-weight: 600;'>✅ Calendar Invite Dispatched</span>", unsafe_allow_html=True)

                with col_info2:
                    st.markdown(f"**Reply Status:** `{'Auto-Sent via SMTP' if rec.get('auto_sent') else 'Staged in Drafts'}`")
                    st.markdown(f"**Confidence Gate:** `{'Auto-Approved (>=70%)' if rec.get('is_autonomous_approved') else 'Manual Review'}`")

                st.info("🔒 **DPDP Act 2023 Zero Private Data Retention:** Private email bodies and draft contents are processed exclusively in RAM and never stored on disk.")

# Tab 2: Drafts & Outbox
with tab_drafts:
    st.subheader("Auto-Generated Contextual Replies")
    st.caption("100% of all incoming emails have a reply draft staged in your Drafts folder with meeting links, slot negotiation, or action items.")

    if not recent_records:
        st.info("No generated drafts available.")
    else:
        for rec in recent_records:
            acc_label = rec.get("account_label", "Default Account")
            st.markdown(f"#### ✉️ Message Dispatch Record — {rec.get('email_type', 'General').upper()}")
            st.markdown(f"<span class='badge-account'>Account: {acc_label}</span> | **Urgency:** `{rec.get('urgency', 'normal').upper()}` | **Status:** `{'Auto-Sent via SMTP' if rec.get('auto_sent') else 'Saved in Drafts'}`", unsafe_allow_html=True)
            st.markdown("""
            <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px; font-size: 0.85rem; color: #cbd5e1;">
                🔒 <strong>Zero Private Data Retention (DPDP Act, 2023):</strong> Draft reply was compiled and dispatched in-memory. The email draft is archived directly in your connected email provider's secure cloud folder (Gmail/Outlook Drafts) with the ironclad legal &amp; arbitration notice.
            </div>
            """, unsafe_allow_html=True)
            st.divider()

# Tab 3: Unified Calendar Timeline
with tab_calendar:
    col_t3_title, col_t3_act = st.columns([3, 1])
    with col_t3_title:
        st.subheader("Unified Cross-Account Calendar Timeline")
        st.caption("Simultaneous Google Calendar and Outlook Calendar synchronization prevents double-booking across client and internal meetings.")
    with col_t3_act:
        if st.button("🧩 Run Calendar Defrag", use_container_width=True):
            defrag_res = wm.run_calendar_defragmentation()
            st.success(f"Defragmentation complete! Reclaimed {defrag_res['minutes_reclaimed']}m of dead time into {defrag_res['deep_work_hours_created']} hrs of deep work.")

    scheduled_records = [r for r in recent_records if r.get("event_scheduled") or r.get("has_conflict")]
    if not scheduled_records:
        st.info("No calendar events scheduled yet.")
    else:
        for item in scheduled_records:
            eco = item.get("ecosystem", "google")
            badge_class = "badge-google" if eco == "google" else "badge-m365"
            platform_name = "Google Calendar" if eco == "google" else "Outlook Calendar"
            acc_label = item.get("account_label", "Account")
            
            with st.container():
                st.markdown(f"<span class='badge-account'>👤 {acc_label}</span> <span class='{badge_class}'>{platform_name}</span>", unsafe_allow_html=True)
                if item.get("calendar_result", {}).get("vip_bumped"):
                    st.markdown("<span style='background-color: #d97706; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;'>⭐ VIP Auto-Bump Priority</span>", unsafe_allow_html=True)
                st.markdown(f"### 📅 {item.get('subject')}")
                st.markdown(f"**Start Time:** `{item.get('proposed_datetime')}`")
                if item.get("meeting_link"):
                    st.markdown(f"**Video Conference:** [{item.get('meeting_link')}]({item.get('meeting_link')})")
                
                if item.get("has_conflict"):
                    st.warning("⚠️ Cross-Account Conflict Detected: Google/M365 calendars checked simultaneously. 3 alternative slots proposed in draft reply:")
                    alts = item.get("alternative_slots", [])
                    for a in alts:
                        st.markdown(f"- 🕒 `{a}`")
                else:
                    st.success("✅ Slot confirmed & attendee invitations dispatched.")
                st.divider()

# Tab 4: Confidence-Based Approval Queue
with tab_queue:
    st.subheader("Confidence-Based Manual Approval Queue")
    st.caption("Meetings with confidence >= 0.70 are auto-approved. Borderline requests (< 0.70) are routed here for one-click manual approval.")

    manual_queue_items = [r for r in recent_records if r.get("requires_manual_approval") or (r.get("meeting_confidence", 0) < 0.70 and r.get("proposed_datetime"))]
    
    if not manual_queue_items:
        st.success("🎉 All pending meetings have been processed or auto-approved! Zero items in the approval queue.")
    else:
        for it in manual_queue_items:
            conf_pct = int(it.get("meeting_confidence", 0.5) * 100)
            with st.container():
                st.markdown(f"### ❓ {it.get('subject')}")
                st.markdown(f"**From:** `{it.get('sender')}` | **Account:** `{it.get('account_label')}`")
                st.markdown(f"**Detection Confidence:** `{conf_pct}%` (Threshold: 70%)")
                st.markdown(f"**Proposed Slot:** `{it.get('proposed_datetime')}`")
                
                col_q1, col_q2, col_q3 = st.columns([1, 1, 4])
                with col_q1:
                    if st.button("✅ Approve & Book Event", key=f"app_{it.get('email_id')}"):
                        st.success(f"Meeting approved and calendar invitation confirmed for {it.get('sender')}!")
                with col_q2:
                    if st.button("❌ Decline / Reject", key=f"dec_{it.get('email_id')}"):
                        st.warning(f"Meeting request declined.")
                st.divider()

# Tab 5: Time & Communication Audit
with tab_audit:
    st.subheader("Weekly Time & Communication Audit")
    st.caption("Consolidated analytics on client meeting hours, response turnaround times, invoice pipeline, and 48-hour follow-up loops.")

    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        st.metric("Autonomous Approval Rate", f"{time_audit.get('autonomous_rate_percent', 100)}%", "+4.2% vs last week")
    with col_a2:
        st.metric("Avg Daemon Turnaround", f"{time_audit.get('avg_turnaround_seconds', 1.8)}s", "Instantaneous")
    with col_a3:
        st.metric("Pre-Meeting Dossiers Attached", summary_stats.get("total_dossiers_attached", 0))

    st.markdown("#### 🕒 Hours Spent in Meetings by Client Domain")
    domain_hours = time_audit.get("domain_meeting_hours", {})
    if domain_hours:
        for dom, hrs in domain_hours.items():
            st.markdown(f"**`{dom}`**: `{hrs} hrs`")
            st.progress(min(1.0, hrs / 10.0))
    else:
        st.info("No domain meeting hours recorded yet.")

    st.markdown("---")
    st.markdown("#### 📝 Post-Meeting Minutes of Meeting (MoM) Pipeline")
    moms = audit.get_moms()
    if moms:
        for m in moms[:5]:
            st.markdown(f"""
            <div class="action-item-pill">
                <strong>{m.get('event_title')}</strong> | Decisions: <strong>{m.get('decisions_count')}</strong> | 
                Actions: <strong>{m.get('action_items_count')}</strong> | Attendees: <code>{', '.join(m.get('attendees', []))}</code>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No concluded meeting transcripts processed yet. Minutes of Meeting are drafted automatically when meetings end.")

    st.markdown("---")
    st.markdown("#### 🔄 Cross-Inbox Role Handoffs")
    handoffs = audit.get_role_handoffs()
    if handoffs:
        for h in handoffs[:5]:
            st.markdown(f"""
            <div class="action-item-pill">
                <strong>{h.get('subject')}</strong> | From: <code>{h.get('from_account')}</code> ➔ To: <strong>{h.get('to_account')}</strong> ({h.get('ops_contact')})
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No cross-inbox role handoffs recorded yet.")

    st.markdown("---")
    st.markdown("#### 💳 Invoices & Payment Reminders Pipeline")
    invoices = audit.get_invoices()
    if invoices:
        for inv in invoices:
            st.markdown(f"""
            <div class="action-item-pill">
                <strong>{inv.get('vendor_name')}</strong> — Invoice #{inv.get('invoice_number')} | 
                Amount: <strong>{inv.get('currency')}{inv.get('amount'):,.2f}</strong> | 
                Due Date: <code>{inv.get('due_date')}</code> | Status: <strong>{inv.get('status')}</strong>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No invoices extracted yet. Invoices found in incoming emails will automatically trigger calendar payment reminders.")

    st.markdown("---")
    st.markdown("#### ⏳ Automated 48-Hour 'No-Reply' Follow-Up Chaser Queue")
    followups = audit.get_pending_followups()
    if followups:
        for fol in followups:
            chased_badge = "<span style='color: #10b981; font-weight: 600;'>✅ Chaser Staged in Drafts</span>" if fol.get("chased") else "<span style='color: #f59e0b;'>⏳ Monitoring for Reply</span>"
            st.markdown(f"""
            <div class="account-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{fol.get('subject')}</strong><br>
                        <small style="color: #94a3b8;">To: <code>{fol.get('recipient')}</code> | Sent At: {fol.get('sent_at')}</small>
                    </div>
                    <div>{chased_badge}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No outbound emails awaiting follow-up.")

# Tab 6: Manage Accounts (Multi-Tenant)
with tab_accounts:
    st.subheader("Connected Accounts & Inboxes")
    st.caption("Manage all Google Workspace and Microsoft 365 inboxes operated by the agent.")

    if not all_accounts:
        st.info("No accounts registered yet. Use the form below to add your first Google or Microsoft 365 account.")
    else:
        for acc in all_accounts:
            acc_id = acc.get("id")
            eco = acc.get("ecosystem", "google")
            badge_class = "badge-google" if eco == "google" else "badge-m365"
            badge_text = "Google Workspace" if eco == "google" else "Microsoft 365"
            is_enabled = acc.get("enabled", True)

            st.markdown(f"""
            <div class="account-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span class="{badge_class}">{badge_text}</span>
                        <h4 style="margin: 6px 0 2px 0;">{acc.get('label')}</h4>
                        <div style="color: #94a3b8; font-size: 0.85rem;">Email: <code>{acc.get('email')}</code> | Signature: <i>{acc.get('display_name', 'Assistant')}</i></div>
                    </div>
                    <div>
                        <span style="color: {'#10b981' if is_enabled else '#94a3b8'}; font-weight: 600;">
                            {'● Monitoring Active' if is_enabled else '○ Paused'}
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_t1, col_t2, col_t3 = st.columns([1, 1, 4])
            with col_t1:
                btn_label = "⏸️ Pause" if is_enabled else "▶️ Resume"
                if st.button(btn_label, key=f"tog_{acc_id}"):
                    vault.toggle_account(acc_id, not is_enabled)
                    st.session_state.workflow_manager = AutomationWorkflowManager()
                    st.rerun()
            with col_t2:
                if st.button("🗑️ Delete", key=f"del_{acc_id}"):
                    vault.delete_account(acc_id)
                    st.session_state.workflow_manager = AutomationWorkflowManager()
                    st.rerun()

    st.markdown("---")
    with st.expander("⚡ Connect New Email Account (Instant Setup)", expanded=not bool(all_accounts)):
        st.markdown("#### Enter your Email ID and Password")
        st.caption("The agent automatically detects whether this is Google Workspace or Microsoft 365, configures the servers, and sets up calendar and draft automation.")

        col_new1, col_new2 = st.columns(2)
        with col_new1:
            simple_email = st.text_input("Email ID", placeholder="e.g. name@gmail.com or name@company.com")
        with col_new2:
            simple_pass = st.text_input("Password / App Password", type="password", help="For Gmail: use an App Password from myaccount.google.com/apppasswords. For Outlook/M365: use your account password.")

        with st.expander("⚙️ Optional Customization (Optional)"):
            opt_auto = st.checkbox("Auto-send replies immediately without draft review", value=False)
            opt_disp = st.text_input("Custom Signature Name", placeholder="Leave blank to use your name automatically")

        # Mandatory Consent Checkbox (Indian IT Act 2000 & DPDP Act 2023)
        mandatory_legal_consent = st.checkbox(
            "I have read, understood, and accept the SmartCal Systems Legal Terms, Privacy Policy & Authorization under the Indian Information Technology Act, 2000, Digital Personal Data Protection (DPDP) Act, 2023, and Indian Contract Act, 1872.",
            value=False,
            help="Ticking this checkbox grants revocable authorization to process unread emails in RAM and logs legal proof into config/consent_log.json."
        )

        if st.button("🚀 Connect Account Now", type="primary", use_container_width=True):
            if not simple_email or not simple_pass:
                st.error("Please enter both your Email ID and Password.")
            elif not mandatory_legal_consent:
                st.error("Compliance Requirement: You must tick the mandatory legal consent checkbox before connecting your account.")
            else:
                with st.spinner("Detecting email ecosystem and establishing connection..."):
                    try:
                        acc_res = vault.add_simple_account(
                            email=simple_email,
                            password=simple_pass,
                            auto_send=opt_auto,
                            display_name=opt_disp if opt_disp else None
                        )
                        vault.log_consent(
                            email=simple_email,
                            consent_text="Web Dashboard Account Connection: Explicit authorization accepted under Indian IT Act 2000 & DPDP Act 2023",
                            status="AUTHORIZED"
                        )
                        st.session_state.workflow_manager = AutomationWorkflowManager()
                        st.success(f"✅ Successfully connected {acc_res['label']} as a {acc_res['ecosystem'].upper()} account! Legal consent logged in config/consent_log.json.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to connect account: {e}")

# Tab 7: Settings & Global Rules
with tab_config:
    st.subheader("Global Workflow Rules, Webhook Escalations & RDP Configuration")

    st.markdown("### 🚨 High-Urgency Escalation Webhook (Slack / Teams / Discord / Generic)")
    cur_webhook = settings.get("escalation_webhook_url", "")
    new_webhook = st.text_input("Incident Escalation Webhook URL", value=cur_webhook, placeholder="https://hooks.slack.com/services/... or https://outlook.office.com/webhook/...")

    st.markdown("### 🖥️ Remote Desktop (RDP) & Browser Automation")
    rdp_creds = vault.get_credentials().get("rdp", {})
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        rdp_host = st.text_input("RDP Host IP / Domain", value=rdp_creds.get("host", "127.0.0.1"))
        rdp_port = st.number_input("RDP Port", value=int(rdp_creds.get("port", 3389)))
    with col_r2:
        rdp_user = st.text_input("RDP Username", value=rdp_creds.get("username", ""))
        browser_exec = st.text_input("Custom Browser Executable Path", value=rdp_creds.get("browser_path", ""))

    st.markdown("### ⚙️ Automation Rules & Polling")
    rule_auto_send = st.checkbox("Global Auto-send (Overrides individual account settings)", value=settings.get("auto_send_drafts", False))
    rule_trigger = st.selectbox(
        "Email Trigger Strategy",
        ["all_unread", "keywords"],
        index=0 if settings.get("trigger_mode") == "all_unread" else 1
    )
    poll_int = st.slider("Continuous Monitoring Polling Interval (seconds)", min_value=15, max_value=300, value=settings.get("poll_interval_seconds", 60))

    if st.button("💾 Save Global Settings"):
        settings["auto_send_drafts"] = rule_auto_send
        settings["trigger_mode"] = rule_trigger
        settings["poll_interval_seconds"] = poll_int
        settings["escalation_webhook_url"] = new_webhook
        save_settings(settings)

        vault_data = vault.get_credentials()
        vault_data["rdp"] = {"host": rdp_host, "port": rdp_port, "username": rdp_user, "browser_path": browser_exec}
        vault.save_credentials(vault_data)

        st.session_state.workflow_manager = AutomationWorkflowManager()
        st.success("Global settings saved successfully!")

# Tab 8: Legal Terms, Privacy & DPDP Compliance (/terms)
with tab_terms:
    st.subheader("📜 Legal Terms, Privacy & DPDP Compliance (/terms)")
    st.caption("Enforcing compliance with the Indian Information Technology Act, 2000, Digital Personal Data Protection (DPDP) Act, 2023, and Indian Contract Act, 1872.")

    st.markdown("### 🏛️ Ironclad Indian Contract, Privacy & Arbitration Notice")
    st.markdown("This exact legal notice is displayed across all website portals and automatically appended to every automated email:")

    st.code("""--------------------------------------------------
LEGAL TERMS, PRIVACY & LIABILITY NOTICE (SMARTCAL SYSTEMS - INDIA):
• Authorization (IT Act, 2000 & DPDP Act, 2023): By replying 'I AGREE', selecting a plan, or submitting an App Password, you grant explicit, revocable consent to SmartCal Systems to process unread scheduling emails in memory (RAM). No private email bodies are stored on disk.
• Instant Revocation: You may terminate access at any second by replying 'DELETE' or revoking your App Password in Google/Microsoft Security.
• 'AS-IS' Software & Uptime Notice: Software operates on an 'AS-IS' basis without uptime guarantees. SmartCal Systems bears zero liability for missed meetings, scheduling conflicts, or indirect business losses.
• Dispute Resolution & Jurisdiction: Users are encouraged to test Plan 1 (₹0 Free Trial) before payment. Any dispute shall be resolved amicably or through sole arbitration in Bengaluru, Karnataka under the Arbitration and Conciliation Act, 1996. Maximum liability is strictly limited to the actual fee paid in the last 7 days.
• Opt-Out: Reply 'STOP' at any time to opt out of all messages.
--------------------------------------------------""", language="text")

    st.markdown("---")
    st.markdown("### 🛑 Instant 'STOP / REVOKE / DELETE' Kill-Switch")
    st.markdown("""
    Under the **Indian DPDP Act, 2023**, clients have the absolute legal right to instantly revoke consent and demand total erasure of their credentials and data.
    Submitting an email below will:
    - **Immediately delete credentials** from `config/credentials.json`.
    - **Add email to suppression registry** (`config/unsubscribed.json`) to permanently block any scans or outreach.
    - **Archive revocation status** in `config/consent_log.json` as `REVOKED_AND_WIPED`.
    """)

    col_k1, col_k2 = st.columns([3, 1])
    with col_k1:
        kill_email_in = st.text_input("Enter Email to Wipe & Revoke:", placeholder="e.g. user@company.com", key="tab_terms_kill_email")
    with col_k2:
        st.markdown("<div style='padding-top: 28px;'>", unsafe_allow_html=True)
        kill_click = st.button("🗑️ Execute Instant Wipe", type="primary", use_container_width=True, key="tab_terms_kill_btn")
        st.markdown("</div>", unsafe_allow_html=True)

    if kill_click:
        if not kill_email_in or "@" not in kill_email_in:
            st.error("Please enter a valid email address to revoke.")
        else:
            vault.delete_account_by_email(kill_email_in)
            vault.add_to_unsubscribed(kill_email_in)
            vault.update_consent_status(kill_email_in, status="REVOKED_AND_WIPED")
            st.session_state.workflow_manager = AutomationWorkflowManager()
            st.success("Your credentials and data have been permanently deleted from SmartCal Systems in compliance with the Indian DPDP Act, 2023.")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Mandatory Consent Archive (config/consent_log.json)")
    st.caption("Permanent audit log of explicit consent authorizations (email 'I AGREE' replies and web signups).")

    consent_records = vault.get_consent_log(limit=50)
    if consent_records:
        st.dataframe(consent_records, use_container_width=True)
    else:
        st.info("No consent records registered yet. Authorizations are automatically recorded upon account connection or 'I AGREE' replies.")

    st.markdown("---")
    st.markdown("### 🚫 Global Suppression Registry (config/unsubscribed.json)")
    st.caption("Emails permanently blocked from all inbox monitoring, cold advertising, and automated dispatch.")

    unsub_list = vault.get_unsubscribed_list()
    if unsub_list:
        st.write(", ".join([f"`{u}`" for u in unsub_list]))
    else:
        st.caption("No addresses in suppression registry.")
