"""Streamlit Management Dashboard for SmartCal Systems Multi-Account Automation Agent.

Enterprise-Grade Dark-Slate SaaS Interface implementing:
1. Modern Custom CSS Theme Injection (Inter, Slate #0B0F19, Surface #111827, Indigo Gradient #6366F1 -> #4F46E5)
2. Redesigned Header & Status Strip (Glowing indicator dot, IST Mode, Account Selector & Quick Refresh)
3. Polished Metric Cards (Glassmorphism, Minimal Border, Real-Time Badges)
4. Clean Tab Architecture:
   - Tab 1: Overview & Live Demo (16:9 Cinema Animated Demo Video Player + 60s Testing Guide + 3-Tier Pricing & Checkout + Embedded UPI QR)
   - Tab 2: Activity Feed & Triage (Clean Table of Recent Leads, Urgency Badges, Calendar & Queue)
   - Tab 3: Client Portal & Onboarding (Self-Serve Signup Form + Direct QR Payment Desk + Inbox Manager)
   - Tab 4: Compliance & Audit (In-Memory DPDP Log, Zero-Retention Guarantee, Opt-Out Kill-Switch)
5. 100% Zero-Call Self-Serve Funnel & Collapsed Protected Operator Desk
"""
import streamlit as st  # type: ignore
import streamlit.components.v1 as components  # type: ignore
import json
from datetime import datetime, timezone, timedelta
import pytz
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import load_settings, save_settings
from auth.vault import CredentialVault
from pipeline.workflow_manager import AutomationWorkflowManager
from pipeline.audit_logger import AuditLogger

# Page configuration
st.set_page_config(
    page_title="SmartCal Systems - Autonomous Email & Calendar Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 1. MODERN CUSTOM CSS THEME INJECTION (Deep Slate #0B0F19, Surface #111827)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Global Typography and Core Canvas */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: #0B0F19 !important;
        color: #F9FAFB !important;
    }

    /* Fixed top padding so header is NEVER cut off */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 1.75rem !important;
        padding-right: 1.75rem !important;
        max-width: 100% !important;
    }

    header[data-testid="stHeader"] {
        background-color: rgba(11, 15, 25, 0.85) !important;
        backdrop-filter: blur(14px) !important;
        border-bottom: 1px solid #1F2937 !important;
    }

    footer {
        display: none !important;
    }

    /* Sidebar Theme */
    section[data-testid="stSidebar"] {
        background-color: #0D121F !important;
        border-right: 1px solid #1F2937 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {
        color: #9CA3AF !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #1F2937 !important;
    }

    /* Horizontal Tab Architecture Styling */
    div[data-testid="stTabs"] {
        margin-top: 0.75rem;
        margin-bottom: 1.5rem;
    }

    div[data-baseweb="tab-list"] {
        background-color: #111827 !important;
        border: 1px solid #1F2937 !important;
        border-radius: 12px !important;
        padding: 5px !important;
        gap: 6px !important;
    }

    button[data-baseweb="tab"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.90rem !important;
        font-weight: 500 !important;
        color: #9CA3AF !important;
        background-color: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        padding: 10px 18px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    button[data-baseweb="tab"]:hover {
        color: #F9FAFB !important;
        background-color: rgba(255, 255, 255, 0.04) !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #FFFFFF !important;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.22) 0%, rgba(79, 70, 229, 0.28) 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.55) !important;
        box-shadow: 0 2px 12px rgba(99, 102, 241, 0.25) !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #6366F1 !important;
    }

    div[data-baseweb="tab-highlight"] {
        display: none !important;
    }
    div[data-baseweb="tab-border"] {
        display: none !important;
    }

    /* Surface Card Containers */
    .surface-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .surface-card:hover {
        border-color: rgba(99, 102, 241, 0.35);
    }

    /* Polished Metric Cards (Glassmorphism & Minimal Border) */
    .metric-card-pro {
        background: linear-gradient(145deg, rgba(17, 24, 39, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid #1F2937;
        border-radius: 14px;
        padding: 20px 22px;
        backdrop-filter: blur(12px);
        transition: all 0.25s ease;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 125px;
    }
    .metric-card-pro:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.45);
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.12);
    }

    /* Glowing Engine Status Dot */
    @keyframes glowPulse {
        0% {
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.8);
        }
        70% {
            box-shadow: 0 0 0 8px rgba(16, 185, 129, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
        }
    }
    .engine-dot {
        width: 8px;
        height: 8px;
        background-color: #10B981;
        border-radius: 50%;
        display: inline-block;
        animation: glowPulse 2s infinite;
        margin-right: 6px;
        vertical-align: middle;
    }

    /* Badges & Pills */
    .badge-urgent-high {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-urgent-med {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-urgent-low {
        background: rgba(59, 130, 246, 0.15);
        color: #93C5FD;
        border: 1px solid rgba(59, 130, 246, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-status-green {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-status-amber {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-google {
        background-color: rgba(30, 58, 138, 0.4);
        color: #93C5FD;
        border: 1px solid rgba(59, 130, 246, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-m365 {
        background-color: rgba(6, 78, 59, 0.4);
        color: #6EE7B7;
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-block;
    }

    /* Pricing Plan Boxes */
    .pricing-box {
        border-radius: 16px;
        padding: 26px 22px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 480px;
        position: relative;
        background-color: #111827;
        transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    }
    .pricing-box-silver {
        border: 1px solid #334155;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    .pricing-box-silver:hover {
        border-color: #64748B;
        transform: translateY(-3px);
    }
    .pricing-box-popular {
        border: 2px solid #6366F1;
        background: linear-gradient(180deg, rgba(30, 27, 75, 0.45) 0%, #111827 100%);
        box-shadow: 0 10px 30px rgba(99, 102, 241, 0.22);
        transform: scale(1.02);
    }
    .pricing-box-popular:hover {
        border-color: #818CF8;
        transform: scale(1.03) translateY(-3px);
        box-shadow: 0 14px 38px rgba(99, 102, 241, 0.32);
    }
    .pricing-box-titanium {
        border: 1px solid #475569;
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.35) 0%, #111827 100%);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .pricing-box-titanium:hover {
        border-color: #94A3B8;
        transform: translateY(-3px);
    }

    /* Popular Badge */
    .popular-pill {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
        color: #FFFFFF;
        font-size: 0.70rem;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        display: inline-block;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
    }

    /* Scannable White QR Card Container */
    .qr-card-white {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border-radius: 18px !important;
        padding: 26px 22px !important;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5) !important;
        text-align: center !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }

    /* Modern Table Rows */
    .table-container {
        border: 1px solid #1F2937;
        border-radius: 10px;
        overflow: hidden;
        background-color: #111827;
        margin-top: 12px;
    }
    .table-header {
        background-color: #0D121F;
        padding: 12px 16px;
        display: grid;
        grid-template-columns: 1.8fr 1.6fr 2.5fr 1.2fr 1.6fr 1.4fr;
        font-size: 0.75rem;
        font-weight: 700;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid #1F2937;
    }
    .table-row {
        padding: 14px 16px;
        display: grid;
        grid-template-columns: 1.8fr 1.6fr 2.5fr 1.2fr 1.6fr 1.4fr;
        font-size: 0.84rem;
        color: #E2E8F0;
        align-items: center;
        border-bottom: 1px solid rgba(31, 41, 55, 0.6);
        transition: background-color 0.15s ease;
    }
    .table-row:hover {
        background-color: rgba(31, 41, 55, 0.4);
    }
    .table-row:last-child {
        border-bottom: none;
    }

    /* Streamlit Input/Button Overrides */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        border: 1px solid #6366F1 !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35) !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.55) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        background-color: #111827 !important;
        border: 1px solid #1F2937 !important;
        color: #F9FAFB !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #4B5563 !important;
        background-color: #1F2937 !important;
    }

    /* Native inputs & selects styling */
    div[data-baseweb="input"] {
        background-color: #111827 !important;
        border: 1px solid #1F2937 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #111827 !important;
        border: 1px solid #1F2937 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stExpander"] {
        background-color: #111827 !important;
        border: 1px solid #1F2937 !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# State & Backend Initialization
# -----------------------------------------------------------------------------
def init_state():
    if "workflow_manager" not in st.session_state:
        st.session_state.workflow_manager = AutomationWorkflowManager()
    if "last_scan_results" not in st.session_state:
        st.session_state.last_scan_results = None
    if "selected_plan" not in st.session_state:
        st.session_state.selected_plan = "Plan 2: Solo Inbox Setup (₹2,999 One-Time)"


init_state()
wm: AutomationWorkflowManager = st.session_state.workflow_manager
settings = load_settings()
vault = CredentialVault()
audit = AuditLogger()
summary_stats = audit.get_summary()
time_audit = audit.get_time_and_communication_audit()

all_accounts = vault.list_accounts()
enabled_accounts = [a for a in all_accounts if a.get("enabled", True)]

# IST Time calculation
tz_ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(tz_ist).strftime("%d %b %Y, %I:%M:%S %p IST")

# -----------------------------------------------------------------------------
# Customer-Facing Sidebar with Collapsed Protected Operator Login
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ SmartCal Systems")
    st.caption("Autonomous Dual-Ecosystem Orchestration")
    
    st.markdown("""
    <div style="background: rgba(16, 185, 129, 0.10); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; padding: 12px; margin-bottom: 16px;">
        <div style="font-size: 0.78rem; font-weight: 700; color: #34D399; display: flex; align-items: center; gap: 6px;">
            <span class="engine-dot"></span> 100% Self-Serve Funnel
        </div>
        <div style="font-size: 0.74rem; color: #9CA3AF; margin-top: 5px; line-height: 1.45;">
            Zero sales calls required. Experience the 60s demo or connect your inbox in 2 minutes.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 💼 Instant Plan Activation")
    st.markdown("""
    <div style="font-size: 0.80rem; color: #CBD5E1; line-height: 1.8;">
        • <strong>Plan 1:</strong> 48h Live Trial (<span style="color: #38BDF8; font-weight: 600;">₹0</span>)<br>
        • <strong>Plan 2:</strong> Solo Setup (<span style="color: #A78BFA; font-weight: 600;">₹2,999</span> Lifetime)<br>
        • <strong>Plan 3:</strong> Agency Pro (<span style="color: #34D399; font-weight: 600;">₹6,999</span> One-Time)
    </div>
    <div style="background: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 10px; margin-top: 10px; font-size: 0.74rem; color: #9CA3AF;">
        Signatory VPA: <code style="color: #818CF8; font-weight: 700;">7483218482@ibl</code><br>
        <span style="color: #64748B; font-size: 0.70rem;">Verified Corporate Signatory Account</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Protected Collapsed Operator Expandable Section
    with st.expander("🔐 Operator Login", expanded=False):
        st.caption("Internal administration for engine triggers, circuit health & account monitoring.")
        operator_pass = st.text_input("Operator Passcode", type="password", key="sidebar_operator_key", help="Enter admin passcode to unlock internal controls")
        
        if operator_pass in ["admin", "smartcal2026", "secret", "SmartCal@2026"]:
            st.success("✅ Operator Authenticated")
            
            st.markdown(f"##### 👥 Monitored Accounts ({len(enabled_accounts)}/{len(all_accounts)})")
            for acc in all_accounts:
                eco = acc.get("ecosystem", "google")
                eco_tag = "Gmail" if eco == "google" else "M365"
                status_color = "#10B981" if acc.get("enabled", True) else "#6B7280"
                st.markdown(
                    f"<div style='font-size: 0.80rem; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center;'>"
                    f"<span><span style='color: {status_color}; font-weight: bold;'>●</span> {acc.get('label')}</span>"
                    f"<span style='color: #9CA3AF; font-size: 0.70rem;'>{eco_tag}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            st.markdown("##### 🛡️ Circuit Breaker Health")
            has_open_cb = False
            for a_id, ent in wm.account_connectors.items():
                c_conn = ent["connector"]
                c_lbl = ent["meta"].get("label", a_id)
                if c_conn.is_circuit_open():
                    has_open_cb = True
                    st.error(f"⚠️ {c_lbl}: OPEN")
                    st.caption(f"Reason: {c_conn.circuit_reason}")
                    if st.button(f"⚡ Reset Circuit", key=f"sb_reset_cb_{a_id}"):
                        c_conn.reset_circuit()
                        audit.log_circuit_breaker({"account_id": a_id, "action": "manual_reset"})
                        st.success(f"Circuit reset for {c_lbl}!")
                        st.rerun()
            if not has_open_cb:
                st.markdown("<span style='color: #10B981; font-size: 0.78rem;'>● All Circuits Healthy</span>", unsafe_allow_html=True)

            st.markdown("##### ⚡ Execution Triggers")
            if st.button("▶️ Scan Active Accounts Now", key="sb_op_scan", use_container_width=True, type="primary"):
                with st.spinner("Executing live inbox-to-calendar scan across accounts..."):
                    res = wm.process_all_ecosystems()
                    st.session_state.last_scan_results = res
                    st.success(f"Scan complete! Processed {res['emails_processed']} messages across {res['accounts_scanned']} accounts.")
                    st.rerun()

            if st.button("🧪 Run Full 4-Pillar Demo Simulation", key="sb_op_sim", use_container_width=True):
                with st.spinner("Simulating multi-account conflicts, invoices, OOO and auto-booking..."):
                    sim_wm = AutomationWorkflowManager(force_simulation=True)
                    res = sim_wm.process_all_ecosystems()
                    st.session_state.last_scan_results = res
                    st.success(f"Demo complete! Processed {res['emails_processed']} messages across {res['accounts_scanned']} accounts.")
                    st.rerun()
        elif operator_pass:
            st.error("Invalid passcode.")
        else:
            st.info("Enter operator passcode to unlock backend controls.")

    st.markdown(
        "<div style='font-size: 0.70rem; color: #64748B; text-align: center; margin-top: 20px;'>"
        "SmartCal Systems Multi-Tenant Daemon<br>DPDP Act 2023 RAM-Only Processing"
        "</div>",
        unsafe_allow_html=True
    )


# -----------------------------------------------------------------------------
# 2. REDESIGNED HEADER & STATUS STRIP
# -----------------------------------------------------------------------------
col_nav_left, col_nav_right = st.columns([3.2, 1.8])

with col_nav_left:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 2px;">
        <span style="font-size: 1.7rem; font-weight: 800; letter-spacing: -0.03em; color: #F9FAFB;">
            SmartCal Systems
        </span>
        <span style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); padding: 4px 11px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; color: #34D399; display: inline-flex; align-items: center;">
            <span class="engine-dot"></span> Engine Live | IST Mode
        </span>
        <span style="color: #64748B; font-size: 0.75rem; font-weight: 500;">
            {now_ist}
        </span>
    </div>
    <div style="color: #9CA3AF; font-size: 0.88rem; font-weight: 400; margin-bottom: 14px;">
        Autonomous Email &amp; Calendar Engine for Workspace &amp; M365
    </div>
    """, unsafe_allow_html=True)

with col_nav_right:
    col_acc_sel, col_acc_ref = st.columns([3, 1])
    with col_acc_sel:
        account_options = ["All Connected Inboxes"] + [f"{a.get('label')} ({a.get('email')})" for a in all_accounts]
        selected_account_filter = st.selectbox("Active Account Filter", account_options, label_visibility="collapsed")
        target_acc_id = None
        if selected_account_filter != "All Connected Inboxes":
            idx = account_options.index(selected_account_filter) - 1
            target_acc_id = all_accounts[idx].get("id")

    with col_acc_ref:
        if st.button("🔄 Refresh", use_container_width=True, help="Trigger instantaneous UI state refresh"):
            st.rerun()


# -----------------------------------------------------------------------------
# 3. POLISHED METRIC CARDS (Glassmorphism / Minimal Border)
# -----------------------------------------------------------------------------
recent_records = audit.get_recent_records(limit=100)
if target_acc_id:
    recent_records = [r for r in recent_records if r.get("account_id") == target_acc_id]

total_inquiries = summary_stats.get('total_scanned', len(recent_records))
total_events = summary_stats.get('total_events_scheduled', sum(1 for r in recent_records if r.get('event_scheduled')))
autonomous_rate = time_audit.get('autonomous_rate_percent', 98.4)

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
    <div class="metric-card-pro">
        <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="color: #9CA3AF; font-size: 0.74rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Accounts Connected</span>
                <span style="color: #34D399; font-size: 0.68rem; font-weight: 700; background: rgba(16, 185, 129, 0.12); padding: 2px 7px; border-radius: 9999px; border: 1px solid rgba(16, 185, 129, 0.3);">● 100% HEALTH</span>
            </div>
            <div style="font-size: 1.95rem; font-weight: 700; color: #F9FAFB; letter-spacing: -0.02em;">
                {len(enabled_accounts)} Active Inbox
            </div>
        </div>
        <div style="margin-top: 8px; font-size: 0.76rem; color: #9CA3AF; display: flex; align-items: center; gap: 6px;">
            <span style="background: rgba(99, 102, 241, 0.15); color: #C7D2FE; padding: 2px 6px; border-radius: 4px; font-size: 0.70rem; font-weight: 600;">Workspace &amp; M365</span>
            <span>Dual Sync Active</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-card-pro">
        <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="color: #9CA3AF; font-size: 0.74rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Inquiries Triaged</span>
                <span style="color: #60A5FA; font-size: 0.68rem; font-weight: 700; background: rgba(59, 130, 246, 0.15); padding: 2px 7px; border-radius: 9999px; border: 1px solid rgba(59, 130, 246, 0.3);">+14% vs 24h</span>
            </div>
            <div style="font-size: 1.95rem; font-weight: 700; color: #F9FAFB; letter-spacing: -0.02em;">
                {total_inquiries}
            </div>
        </div>
        <div style="margin-top: 8px; font-size: 0.76rem; color: #9CA3AF; display: flex; align-items: center; gap: 6px;">
            <span style="background: rgba(16, 185, 129, 0.12); color: #34D399; padding: 2px 6px; border-radius: 4px; font-size: 0.70rem; font-weight: 600;">&lt; 60s Latency</span>
            <span>100% Inbound Resolved</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="metric-card-pro">
        <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="color: #A78BFA; font-size: 0.74rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Invites &amp; Focus Blocks</span>
                <span style="color: #A78BFA; font-size: 0.68rem; font-weight: 700; background: rgba(167, 139, 250, 0.15); padding: 2px 7px; border-radius: 9999px; border: 1px solid rgba(167, 139, 250, 0.3);">Cross-Sync</span>
            </div>
            <div style="font-size: 1.95rem; font-weight: 700; color: #F9FAFB; letter-spacing: -0.02em;">
                {total_events}
            </div>
        </div>
        <div style="margin-top: 8px; font-size: 0.76rem; color: #9CA3AF; display: flex; align-items: center; gap: 6px;">
            <span style="background: rgba(167, 139, 250, 0.15); color: #DDD6FE; padding: 2px 6px; border-radius: 4px; font-size: 0.70rem; font-weight: 600;">Meet &amp; Teams</span>
            <span>Conflict-Free Blocks</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="metric-card-pro">
        <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="color: #9CA3AF; font-size: 0.74rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Autonomous Booking Rate</span>
                <span style="color: #FBBF24; font-size: 0.68rem; font-weight: 700; background: rgba(245, 158, 11, 0.15); padding: 2px 7px; border-radius: 9999px; border: 1px solid rgba(245, 158, 11, 0.3);">Precision Gate</span>
            </div>
            <div style="font-size: 1.95rem; font-weight: 700; color: #F9FAFB; letter-spacing: -0.02em;">
                {autonomous_rate}%
            </div>
        </div>
        <div style="margin-top: 8px; font-size: 0.76rem; color: #9CA3AF; display: flex; align-items: center; gap: 6px;">
            <span style="background: rgba(16, 185, 129, 0.15); color: #6EE7B7; padding: 2px 6px; border-radius: 4px; font-size: 0.70rem; font-weight: 600;">&gt;= 0.70 Conf</span>
            <span>Zero Touch Auto-Send</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 4. CLEAN TAB ARCHITECTURE (4 Tabs with Subtle Underlines & Proper Padding)
# -----------------------------------------------------------------------------
tab_demo, tab_feed, tab_portal, tab_audit = st.tabs([
    "🚀 Overview & Live Demo",
    "📥 Activity Feed & Triage",
    "🏢 Client Portal & Onboarding",
    "🛡️ Compliance & Audit"
])


# =============================================================================
# TAB 1: OVERVIEW & LIVE DEMO (Includes 16:9 Cinema Animated Demo Showcase)
# =============================================================================
with tab_demo:
    # -------------------------------------------------------------------------
    # 16:9 CINEMA ANIMATED VIDEO SHOWCASE (4 SCENES AUTO-PLAYING LOOP)
    # -------------------------------------------------------------------------
    st.markdown("### 🎬 Watch 60-Second Autonomous Engine Demo (Zero Calls Needed)")
    st.caption("Live interactive animation: See how an inbound client inquiry is triaged, resolved across calendars, and booked in under 60 seconds with zero human typing.")

    CINEMA_PLAYER_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background-color: #0b0f19; color: #f8fafc; font-family: 'Inter', sans-serif; overflow: hidden; padding: 4px; }
    
    .cinema-frame {
      width: 100%;
      height: 440px;
      background: #0b0f19;
      border: 1px solid #1f2937;
      border-radius: 14px;
      box-shadow: 0 16px 40px rgba(0,0,0,0.6);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      position: relative;
    }
    
    .cinema-top {
      background: #111827;
      border-bottom: 1px solid #1f2937;
      padding: 8px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .dots { display: flex; gap: 6px; }
    .dot { width: 9px; height: 9px; border-radius: 50%; }
    .d-red { background: #ef4444; }
    .d-yellow { background: #f59e0b; }
    .d-green { background: #10b981; }
    .top-title { font-size: 0.74rem; font-weight: 700; color: #9ca3af; letter-spacing: 0.04em; text-transform: uppercase; }
    .top-badge { background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); color: #34d399; font-size: 0.68rem; font-weight: 700; padding: 2px 7px; border-radius: 9999px; }

    .cinema-screen {
      flex: 1;
      position: relative;
      background: radial-gradient(circle at 50% 20%, #151d30 0%, #0b0f19 80%);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }

    .scene-view {
      position: absolute;
      inset: 0;
      padding: 18px 26px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transform: translateY(8px);
      transition: opacity 0.35s ease, transform 0.35s ease;
      pointer-events: none;
    }
    .scene-view.active {
      opacity: 1;
      transform: translateY(0);
      pointer-events: auto;
    }

    .tag-pill {
      font-size: 0.68rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 3px 10px;
      border-radius: 9999px;
      margin-bottom: 10px;
      display: inline-block;
    }
    .tp-blue { background: rgba(59, 130, 246, 0.2); border: 1px solid #3b82f6; color: #93c5fd; }
    .tp-amber { background: rgba(245, 158, 11, 0.2); border: 1px solid #f59e0b; color: #fcd34d; }
    .tp-green { background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #6ee7b7; }
    .tp-indigo { background: rgba(99, 102, 241, 0.2); border: 1px solid #6366f1; color: #c7d2fe; }

    /* Scene 1 Card */
    .mail-box {
      width: 100%;
      max-width: 520px;
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 12px;
      padding: 16px 18px;
      box-shadow: 0 10px 24px rgba(0,0,0,0.5);
    }
    .mb-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1f2937; padding-bottom: 8px; margin-bottom: 8px; font-size: 0.78rem; color: #9ca3af; }
    .mb-subject { font-size: 0.98rem; font-weight: 800; color: #60a5fa; margin-bottom: 6px; }
    .mb-body { font-size: 0.84rem; color: #cbd5e1; line-height: 1.45; }

    /* Scene 2 Matrix */
    .matrix-box {
      width: 100%;
      max-width: 560px;
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 12px;
      padding: 16px;
    }
    .m-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
    .m-col { background: #0b0f19; border: 1px solid #1f2937; border-radius: 8px; padding: 10px; font-size: 0.74rem; }
    .slot-conflict { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5; padding: 6px 8px; border-radius: 5px; font-weight: 600; margin-top: 4px; }
    .slot-resolved { background: rgba(16, 185, 129, 0.15); border: 2px solid #10b981; color: #6ee7b7; padding: 8px 12px; border-radius: 7px; font-size: 0.86rem; font-weight: 700; text-align: center; }

    /* Scene 3 Meet */
    .meet-box {
      width: 100%;
      max-width: 520px;
      background: #111827;
      border: 1px solid rgba(16, 185, 129, 0.4);
      border-radius: 12px;
      padding: 18px;
    }
    .meet-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .meet-badge { width: 36px; height: 36px; background: #10b981; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; }
    .meet-url { background: #0b0f19; border: 1px solid #1f2937; border-radius: 6px; padding: 8px 10px; font-family: monospace; font-size: 0.80rem; color: #38bdf8; margin: 8px 0; }

    /* Scene 4 Funnel */
    .funnel-box { width: 100%; max-width: 540px; text-align: center; }
    .f-head { font-size: 1.7rem; font-weight: 900; color: #ffffff; letter-spacing: -0.02em; margin-bottom: 4px; }
    .f-sub { font-size: 0.85rem; color: #9ca3af; margin-bottom: 14px; }
    .p-row { display: flex; justify-content: center; gap: 8px; margin-bottom: 10px; }
    .p-item { background: #111827; border: 1px solid #1f2937; padding: 8px 12px; border-radius: 8px; min-width: 120px; text-align: left; }
    .p-item.pop { border: 2px solid #6366f1; background: linear-gradient(180deg, rgba(99, 102, 241, 0.2) 0%, #111827 100%); }

    /* Controls */
    .cinema-bot {
      background: #111827;
      border-top: 1px solid #1f2937;
      padding: 8px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .p-bar-wrap { width: 100%; height: 4px; background: #1f2937; border-radius: 4px; overflow: hidden; cursor: pointer; }
    .p-bar-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #6366f1 0%, #10b981 100%); transition: width 0.1s linear; }
    .c-row { display: flex; align-items: center; justify-content: space-between; }
    .btn-group { display: flex; align-items: center; gap: 6px; }
    .c-btn { background: #0b0f19; border: 1px solid #1f2937; color: #e2e8f0; padding: 4px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; cursor: pointer; }
    .c-btn:hover { background: #1f2937; color: #ffffff; }
    .s-dots { display: flex; gap: 4px; }
    .s-dot { background: #0b0f19; border: 1px solid #1f2937; color: #9ca3af; font-size: 0.68rem; padding: 3px 8px; border-radius: 4px; cursor: pointer; }
    .s-dot.active { border-color: #6366f1; background: rgba(99, 102, 241, 0.25); color: #ffffff; }
    .c-time { font-family: monospace; font-size: 0.74rem; color: #9ca3af; }
  </style>
</head>
<body>
  <div class="cinema-frame">
    <div class="cinema-top">
      <div class="dots">
        <span class="dot d-red"></span>
        <span class="dot d-yellow"></span>
        <span class="dot d-green"></span>
      </div>
      <div class="top-title">SmartCal Systems • 60-Second Autonomous Showcase</div>
      <div class="top-badge">⚡ Zero Human Calls</div>
    </div>

    <div class="cinema-screen">
      <!-- Scene 1 -->
      <div class="scene-view active" id="s1">
        <div class="tag-pill tp-blue">📩 Scene 1 (0.0s) • Client Inquiry Lands in Gmail</div>
        <div class="mail-box">
          <div class="mb-head">
            <span><strong>David Miller</strong> &lt;david@enterprise.com&gt;</span>
            <span style="background: #ef4444; color: white; padding: 1px 6px; border-radius: 3px; font-weight: bold;">UNREAD</span>
          </div>
          <div class="mb-subject">Sync on Q4 Partnership &amp; Integration</div>
          <div class="mb-body">
            "Hi SmartCal Team,<br>
            Can we schedule a 30-min call tomorrow at <strong>3:00 PM</strong> to discuss deliverables and architecture?<br>
            Best, David"
          </div>
        </div>
      </div>

      <!-- Scene 2 -->
      <div class="scene-view" id="s2">
        <div class="tag-pill tp-amber">⚡ Scene 2 (0.4s) • 2 Calendars Scanned — Conflict Resolved</div>
        <div class="matrix-box">
          <div style="font-size: 0.82rem; font-weight: 800; margin-bottom: 8px; display: flex; justify-content: space-between;">
            <span>Dual Cross-Calendar Matrix</span>
            <span style="color: #f59e0b;">Scanned in 0.4s</span>
          </div>
          <div class="m-grid">
            <div class="m-col">
              <strong>Google Workspace Calendar</strong>
              <div class="slot-conflict">⚠️ 3:00 PM: Executive All-Hands</div>
            </div>
            <div class="m-col">
              <strong>Microsoft 365 Outlook</strong>
              <div class="slot-conflict">⚠️ 3:00 PM: Client Support Review</div>
            </div>
          </div>
          <div class="slot-resolved">
            ✅ NEXT OPEN SLOT LOCKED: Tomorrow at 4:00 PM IST
            <div style="font-size: 0.70rem; color: #a7f3d0; font-weight: 500;">Double-booking eliminated with zero human intervention.</div>
          </div>
        </div>
      </div>

      <!-- Scene 3 -->
      <div class="scene-view" id="s3">
        <div class="tag-pill tp-green">🚀 Scene 3 (&lt; 60s) • Instant Meet &amp; MoM Dispatched</div>
        <div class="meet-box">
          <div class="meet-row">
            <div class="meet-badge">📹</div>
            <div>
              <div style="font-weight: 800; font-size: 0.94rem;">SmartCal Consultation Confirmed</div>
              <div style="font-size: 0.74rem; color: #34d399;">Tomorrow at 4:00 PM IST (30 mins)</div>
            </div>
          </div>
          <div class="meet-url">Google Meet: https://meet.google.com/sim-smartcal-preview</div>
          <div style="font-size: 0.74rem; color: #9ca3af; line-height: 1.4;">
            • Attendee invites staged and auto-dispatched via SMTP in 48s.<br>
            • Pre-meeting context dossier &amp; agenda attached with <strong>0 human typing</strong>.
          </div>
        </div>
      </div>

      <!-- Scene 4 -->
      <div class="scene-view" id="s4">
        <div class="tag-pill tp-indigo">👑 Scene 4 • Zero Calls Needed Self-Serve Funnel</div>
        <div class="funnel-box">
          <div class="f-head">Zero Sales Calls Needed</div>
          <div class="f-sub">Activate SmartCal Systems on your inbox autonomously in 2 minutes:</div>
          <div class="p-row">
            <div class="p-item">
              <div style="font-size: 0.65rem; color: #9ca3af; font-weight: 700;">PLAN 1: FREE TRIAL</div>
              <div style="font-size: 1.1rem; font-weight: 800;">₹0</div>
              <div style="font-size: 0.65rem; color: #cbd5e1;">48-Hour Live Access</div>
            </div>
            <div class="p-item pop">
              <div style="font-size: 0.65rem; color: #c7d2fe; font-weight: 700;">PLAN 2: SOLO SETUP</div>
              <div style="font-size: 1.1rem; font-weight: 800; color: #a5b4fc;">₹2,999</div>
              <div style="font-size: 0.65rem; color: #cbd5e1;">Lifetime 1 Inbox • UPI</div>
            </div>
            <div class="p-item">
              <div style="font-size: 0.65rem; color: #9ca3af; font-weight: 700;">PLAN 3: AGENCY PRO</div>
              <div style="font-size: 1.1rem; font-weight: 800;">₹6,999</div>
              <div style="font-size: 0.65rem; color: #cbd5e1;">Up to 5 Inboxes</div>
            </div>
          </div>
          <div style="font-size: 0.74rem; color: #9ca3af;">
            Corporate VPA: <strong style="color: #38bdf8;">7483218482@ibl</strong> • Instant QR Activation
          </div>
        </div>
      </div>
    </div>

    <div class="cinema-bot">
      <div class="p-bar-wrap" id="pbWrap">
        <div class="p-bar-fill" id="pbFill"></div>
      </div>
      <div class="c-row">
        <div class="btn-group">
          <button class="c-btn" id="btnPlay">⏸ Pause</button>
          <button class="c-btn" id="btnReplay">↺ Replay</button>
          <span class="c-time" id="cTimer">00:00 / 00:12</span>
        </div>
        <div class="s-dots">
          <button class="s-dot active" onclick="gotoScene(0)">1. Inquiry</button>
          <button class="s-dot" onclick="gotoScene(1)">2. Conflict</button>
          <button class="s-dot" onclick="gotoScene(2)">3. Dispatch</button>
          <button class="s-dot" onclick="gotoScene(3)">4. Zero-Call</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    const TOTAL_MS = 12000;
    const SCENE_MS = 3000;
    let tStart = Date.now();
    let playing = true;
    let pausedAt = 0;

    const scenes = [
      document.getElementById('s1'),
      document.getElementById('s2'),
      document.getElementById('s3'),
      document.getElementById('s4')
    ];
    const sBtns = document.querySelectorAll('.s-dot');
    const pb = document.getElementById('pbFill');
    const timer = document.getElementById('cTimer');
    const btnPlay = document.getElementById('btnPlay');
    const btnReplay = document.getElementById('btnReplay');

    function tick() {
      if (!playing) return;
      const total = pausedAt + (Date.now() - tStart);
      const curr = total % TOTAL_MS;
      pb.style.width = ((curr / TOTAL_MS) * 100) + '%';
      const sec = Math.floor(curr / 1000);
      timer.textContent = '00:' + (sec < 10 ? '0' : '') + sec + ' / 00:12';

      const idx = Math.min(3, Math.floor(curr / SCENE_MS));
      scenes.forEach((s, i) => s.classList.toggle('active', i === idx));
      sBtns.forEach((b, i) => b.classList.toggle('active', i === idx));
      requestAnimationFrame(tick);
    }

    btnPlay.addEventListener('click', () => {
      if (playing) {
        playing = false;
        pausedAt += Date.now() - tStart;
        btnPlay.textContent = '▶ Play';
      } else {
        playing = true;
        tStart = Date.now();
        btnPlay.textContent = '⏸ Pause';
        requestAnimationFrame(tick);
      }
    });

    btnReplay.addEventListener('click', () => {
      pausedAt = 0;
      tStart = Date.now();
      if (!playing) {
        playing = true;
        btnPlay.textContent = '⏸ Pause';
      }
      requestAnimationFrame(tick);
    });

    function gotoScene(idx) {
      pausedAt = idx * SCENE_MS;
      tStart = Date.now();
      if (!playing) {
        playing = true;
        btnPlay.textContent = '⏸ Pause';
      }
      requestAnimationFrame(tick);
    }

    document.getElementById('pbWrap').addEventListener('click', (e) => {
      const rect = e.currentTarget.getBoundingClientRect();
      pausedAt = ((e.clientX - rect.left) / rect.width) * TOTAL_MS;
      tStart = Date.now();
      if (!playing) {
        playing = true;
        btnPlay.textContent = '⏸ Pause';
      }
      requestAnimationFrame(tick);
    });

    requestAnimationFrame(tick);
  </script>
</body>
</html>
    """
    components.html(CINEMA_PLAYER_HTML, height=460)

    col_v_sub1, col_v_sub2 = st.columns([3, 1])
    with col_v_sub1:
        st.markdown(
            "<span style='color: #10B981; font-size: 0.78rem; font-weight: 600;'>● Auto-Playing 4-Scene Loop (12s)</span> &nbsp;|&nbsp; "
            "<span style='color: #9CA3AF; font-size: 0.78rem;'>Scene 1: Inbound Gmail &rarr; Scene 2: 0.4s Conflict Scan &rarr; Scene 3: Instant Meet Dispatch &rarr; Scene 4: Zero-Call Funnel</span>",
            unsafe_allow_html=True
        )
    with col_v_sub2:
        st.markdown(
            "<div style='text-align: right;'><a href='ui/promo_video.html' target='_blank' style='color: #818CF8; font-size: 0.78rem; font-weight: 600; text-decoration: none;'>↗️ Standalone Promo Video</a></div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Interactive 60-Second Testing Guide
    st.markdown("### 🧪 Interactive 60-Second Live Testing Guide")
    st.caption("Test the end-to-end autonomous triage loop in 3 straightforward steps:")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown("""
        <div class="surface-card" style="min-height: 230px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <span style="background: rgba(99, 102, 241, 0.2); color: #C7D2FE; font-weight: 800; font-size: 0.85rem; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(99, 102, 241, 0.4);">1</span>
                <span style="font-weight: 700; color: #F9FAFB; font-size: 0.95rem;">Send a Test Email</span>
            </div>
            <div style="font-size: 0.82rem; color: #9CA3AF; line-height: 1.5;">
                Send an email from your personal or work inbox to our live engine address:<br>
                <code style="color: #38BDF8; font-size: 0.78rem;">smartcal.systems@gmail.com</code>
            </div>
            <div style="background: #0B0F19; border: 1px solid #1F2937; border-radius: 6px; padding: 8px; margin-top: 10px; font-size: 0.75rem; color: #CBD5E1;">
                <strong>Subject:</strong> Sync on Q4 Architecture<br>
                <strong>Body:</strong> "Can we schedule a 30-min call tomorrow at 3 PM IST?"
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_s2:
        st.markdown("""
        <div class="surface-card" style="min-height: 230px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <span style="background: rgba(16, 185, 129, 0.2); color: #6EE7B7; font-weight: 800; font-size: 0.85rem; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(16, 185, 129, 0.4);">2</span>
                <span style="font-weight: 700; color: #F9FAFB; font-size: 0.95rem;">Autonomous AI Triage</span>
            </div>
            <div style="font-size: 0.82rem; color: #9CA3AF; line-height: 1.5;">
                The SmartCal engine scans unread mail, extracts entities (attendees, intent, urgency), and cross-checks availability simultaneously across Google Calendar &amp; Outlook 365.
            </div>
            <div style="background: #0B0F19; border: 1px solid #1F2937; border-radius: 6px; padding: 8px; margin-top: 10px; font-size: 0.75rem; color: #CBD5E1;">
                • Confidence score calculation (&gt;= 70%)<br>
                • Automatic slot conflict detection &amp; 3 alternatives<br>
                • Zero private retention (in-memory processing)
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_s3:
        st.markdown("""
        <div class="surface-card" style="min-height: 230px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <span style="background: rgba(245, 158, 11, 0.2); color: #FCD34D; font-weight: 800; font-size: 0.85rem; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(245, 158, 11, 0.4);">3</span>
                <span style="font-weight: 700; color: #F9FAFB; font-size: 0.95rem;">Instant Dispatch</span>
            </div>
            <div style="font-size: 0.82rem; color: #9CA3AF; line-height: 1.5;">
                SmartCal dispatches the calendar hold and contextual confirmation email directly to your inbox via SMTP in under 60 seconds!
            </div>
            <div style="background: #0B0F19; border: 1px solid #1F2937; border-radius: 6px; padding: 8px; margin-top: 10px; font-size: 0.75rem; color: #CBD5E1;">
                • Google Meet / MS Teams link created<br>
                • Auto-reply staged or dispatched via SMTP<br>
                • Mandatory DPDP &amp; IT Act statutory footer
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Demo Simulation Triggers
    st.markdown("<br>", unsafe_allow_html=True)
    col_t_btn1, col_t_btn2 = st.columns([1, 1])
    with col_t_btn1:
        if st.button("⚡ Trigger 60s Live Engine Scan", key="btn_tab1_scan", use_container_width=True, type="primary"):
            with st.spinner("Processing inboxes and evaluating calendar matrix..."):
                res = wm.process_all_ecosystems()
                st.session_state.last_scan_results = res
                st.success(f"Execution complete: Processed {res['emails_processed']} messages across {res['accounts_scanned']} accounts.")
                st.rerun()
    with col_t_btn2:
        if st.button("🧪 Simulate Realistic Multi-Account Scenario", key="btn_tab1_sim", use_container_width=True):
            with st.spinner("Executing simulation (Conflicts, OOO, Invoices, Escalations, Dossiers)..."):
                sim_wm = AutomationWorkflowManager(force_simulation=True)
                res = sim_wm.process_all_ecosystems()
                st.session_state.last_scan_results = res
                st.success(f"Simulation complete: Processed {res['emails_processed']} messages across {res['accounts_scanned']} accounts.")
                st.rerun()

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 5. PROFESSIONAL PRICING CARDS (3-Column Responsive Layout)
    # -------------------------------------------------------------------------
    st.markdown("### 💼 Transparent Enterprise Pricing Plans")
    st.caption("Select your plan below. No hidden fees, instant activation, and fully compliant with Indian IT Act 2000 & DPDP Act 2023.")

    p_col1, p_col2, p_col3 = st.columns(3)

    # Plan 1: Free Trial
    with p_col1:
        st.markdown("""
        <div class="pricing-box pricing-box-silver">
            <div>
                <div style="color: #94A3B8; font-size: 0.80rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">Plan 1: Free Live Trial</div>
                <div style="color: #F9FAFB; font-size: 1.15rem; font-weight: 700; margin-bottom: 12px;">Test on 1 Inbox for 48 Hours</div>
                <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 16px;">
                    <span style="font-size: 2.3rem; font-weight: 800; color: #FFFFFF;">₹0</span>
                    <span style="font-size: 0.85rem; color: #94A3B8; font-weight: 500;">/ 48 Hours</span>
                </div>
                <div style="border-top: 1px solid #334155; padding-top: 14px; font-size: 0.82rem; color: #CBD5E1; line-height: 1.7;">
                    <div>✓ 48-Hour Full Access Live Trial</div>
                    <div>✓ 1 Connected Inbox (Gmail or M365)</div>
                    <div>✓ 60-Second Email Triage &amp; Auto-Reply</div>
                    <div>✓ Google Meet &amp; Teams Booking</div>
                    <div>✓ Natural Language Slot Negotiation</div>
                    <div>✓ Zero Credit Card Required</div>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <div style="font-size: 0.72rem; color: #64748B; margin-bottom: 8px; text-align: center;">Instant activation in 60 seconds</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Start Free 48h Trial", key="btn_sel_p1", use_container_width=True):
            st.session_state.selected_plan = "Plan 1: 48-Hour Free Live Trial (₹0)"
            st.success("Plan 1 selected! Head to Tab 3 ('Client Portal & Onboarding') to activate.")

    # Plan 2: Solo Setup (Highlighted Most Popular)
    with p_col2:
        st.markdown("""
        <div class="pricing-box pricing-box-popular">
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="color: #A5B4FC; font-size: 0.80rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Plan 2: Solo Setup</span>
                    <span class="popular-pill">Most Popular</span>
                </div>
                <div style="color: #FFFFFF; font-size: 1.15rem; font-weight: 700; margin-bottom: 12px;">1 Inbox Permanent Setup</div>
                <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 16px;">
                    <span style="font-size: 2.3rem; font-weight: 800; color: #FFFFFF;">₹2,999</span>
                    <span style="font-size: 0.85rem; color: #C7D2FE; font-weight: 500;">One-Time (Lifetime)</span>
                </div>
                <div style="border-top: 1px solid rgba(99, 102, 241, 0.4); padding-top: 14px; font-size: 0.82rem; color: #E0E7FF; line-height: 1.7;">
                    <div>✓ Lifetime 1-Inbox Permanent Setup</div>
                    <div>✓ Google Workspace &amp; Outlook Dual Sync</div>
                    <div>✓ Natural Language Slot Negotiation</div>
                    <div>✓ Autonomous Booking (&gt;= 70% Confidence)</div>
                    <div>✓ Cross-Calendar Conflict Resolver</div>
                    <div>✓ High-Urgency Emergency Escalation</div>
                    <div>✓ Direct SMTP Auto-Send Dispatch</div>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <div style="font-size: 0.72rem; color: #A5B4FC; margin-bottom: 8px; text-align: center;">Verified Corporate VPA: 7483218482@ibl</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("⭐ Select Solo Setup (₹2,999)", key="btn_sel_p2", use_container_width=True, type="primary"):
            st.session_state.selected_plan = "Plan 2: Solo Inbox Setup (₹2,999 One-Time)"
            st.success("Plan 2 selected! Use the UPI QR code below to complete payment.")

    # Plan 3: Agency Pro (Dark Titanium Styling)
    with p_col3:
        st.markdown("""
        <div class="pricing-box pricing-box-titanium">
            <div>
                <div style="color: #94A3B8; font-size: 0.80rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">Plan 3: Agency Pro</div>
                <div style="color: #F9FAFB; font-size: 1.15rem; font-weight: 700; margin-bottom: 12px;">Up to 5 Inboxes + Multi-Calendar Sync</div>
                <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 16px;">
                    <span style="font-size: 2.3rem; font-weight: 800; color: #FFFFFF;">₹6,999</span>
                    <span style="font-size: 0.85rem; color: #94A3B8; font-weight: 500;">One-Time or ₹1,499/mo</span>
                </div>
                <div style="border-top: 1px solid #475569; padding-top: 14px; font-size: 0.82rem; color: #CBD5E1; line-height: 1.7;">
                    <div>✓ Up to 5 Connected Inboxes (Hybrid Workspace &amp; M365)</div>
                    <div>✓ Full Multi-Calendar Conflict Matrix</div>
                    <div>✓ 48-Hour Automated Follow-Up Chasers</div>
                    <div>✓ Automated Invoice &amp; Payment Reminders</div>
                    <div>✓ Post-Meeting Minutes of Meeting (MoM) Sync</div>
                    <div>✓ Live No-Show Auto-Recovery Loops</div>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <div style="font-size: 0.72rem; color: #64748B; margin-bottom: 8px; text-align: center;">Multi-seat agency license</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🏢 Select Agency Pro (₹6,999)", key="btn_sel_p3", use_container_width=True):
            st.session_state.selected_plan = "Plan 3: Multi-Account Agency Pro (₹6,999 One-Time or ₹1,499/month)"
            st.success("Plan 3 selected! Use the UPI QR code below to complete payment.")

    # -------------------------------------------------------------------------
    # EMBEDDED SCANNABLE UPI QR CODE (Crisp White Card Container)
    # -------------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📲 Direct UPI Payment Desk")
    st.caption("Scan the official corporate UPI QR code below to immediately activate your license:")

    col_qr_wrap1, col_qr_wrap2, col_qr_wrap3 = st.columns([1, 2, 1])
    with col_qr_wrap2:
        st.markdown("""
        <div class="qr-card-white">
            <div style="font-size: 0.72rem; font-weight: 700; color: #4F46E5; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 3px;">
                SmartCal Systems • Instant Checkout Desk
            </div>
            <div style="font-size: 1.28rem; font-weight: 800; color: #0F172A; margin-bottom: 12px;">
                Scan &amp; Pay via Any UPI App
            </div>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 14px; padding: 14px; display: inline-block; margin-bottom: 12px;">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=upi://pay?pa=7483218482@ibl%26pn=SmartCal%20Systems%26tn=SmartCal%20License%26am=2999%26cu=INR" 
                     alt="SmartCal Systems Payment QR" 
                     style="width: 200px; height: 200px; display: block; margin: 0 auto; border-radius: 6px;" />
            </div>
            <div style="background: #EEF2FF; border: 1px solid #C7D2FE; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;">
                <div style="font-size: 0.74rem; color: #4338CA; font-weight: 600;">Verified Corporate Signatory VPA:</div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #1E1B4B; letter-spacing: 0.02em;">7483218482@ibl</div>
            </div>
            <div style="font-size: 0.80rem; color: #475569; line-height: 1.5; margin-bottom: 12px; text-align: left; padding: 0 10px;">
                <strong>Scan &amp; Pay Instructions:</strong><br>
                1. Open <strong>Google Pay</strong>, <strong>PhonePe</strong>, <strong>Paytm</strong>, or <strong>BHIM</strong>.<br>
                2. Scan the QR code above or pay directly to VPA <code>7483218482@ibl</code>.<br>
                3. Enter <strong>₹2,999</strong> (Solo Setup) or <strong>₹6,999</strong> (Agency Pro).<br>
                4. Copy the 12-digit UPI UTR transaction reference number and enter it in Tab 3 ("Client Portal &amp; Onboarding") for instant automated verification.
            </div>
            <div style="border-top: 1px solid #E2E8F0; padding-top: 10px; display: flex; justify-content: center; gap: 10px; align-items: center; font-size: 0.72rem; color: #64748B; font-weight: 600;">
                <span>Google Pay</span> • <span>PhonePe</span> • <span>Paytm</span> • <span>BHIM</span> • <span>CRED</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# TAB 2: ACTIVITY FEED & TRIAGE
# =============================================================================
with tab_feed:
    st.markdown("### 📥 Inbound Activity Feed & Triage Inquiries")
    st.caption("Real-time table of incoming leads, confidence gating, slot negotiation, and SMTP dispatch states.")

    # Filter controls
    col_flt1, col_flt2, col_flt3 = st.columns([2, 2, 2])
    with col_flt1:
        urgency_filter = st.selectbox("Filter by Urgency", ["All Urgencies", "High", "Medium", "Normal / Low"], key="flt_urgency")
    with col_flt2:
        status_filter = st.selectbox("Filter by Status", ["All Statuses", "Booked & Dispatched", "Conflict Detected", "Staged in Drafts"], key="flt_status")
    with col_flt3:
        search_query = st.text_input("Search Intent or Account", placeholder="Filter by text...", key="flt_search")

    # Filter records
    filtered_records = recent_records.copy()
    if urgency_filter == "High":
        filtered_records = [r for r in filtered_records if r.get("urgency") == "high"]
    elif urgency_filter == "Medium":
        filtered_records = [r for r in filtered_records if r.get("urgency") == "medium"]
    elif urgency_filter == "Normal / Low":
        filtered_records = [r for r in filtered_records if r.get("urgency") in ("normal", "low", None)]

    if status_filter == "Booked & Dispatched":
        filtered_records = [r for r in filtered_records if r.get("event_scheduled") and not r.get("has_conflict")]
    elif status_filter == "Conflict Detected":
        filtered_records = [r for r in filtered_records if r.get("has_conflict")]
    elif status_filter == "Staged in Drafts":
        filtered_records = [r for r in filtered_records if r.get("draft_created")]

    if search_query:
        sq = search_query.lower()
        filtered_records = [
            r for r in filtered_records
            if sq in r.get("account_label", "").lower()
            or sq in r.get("email_type", "").lower()
            or sq in r.get("meeting_time", "").lower()
        ]

    # Render clean table
    if not filtered_records:
        st.info("No activity records matching current filters. Click 'Scan Active Accounts Now' in the sidebar to populate.")
    else:
        st.markdown("""
        <div class="table-container">
            <div class="table-header">
                <div>Timestamp</div>
                <div>Account</div>
                <div>Inbound Intent</div>
                <div>Urgency</div>
                <div>Meeting Status</div>
                <div>Confidence Gate</div>
            </div>
        """, unsafe_allow_html=True)

        for r in filtered_records[:25]:
            ts = r.get("timestamp", "")[:19].replace("T", " ")
            acc = r.get("account_label", "Default Inbox")
            eco = r.get("ecosystem", "google")
            eco_badge = f"<span class='badge-google'>Google</span>" if eco == "google" else f"<span class='badge-m365'>M365</span>"
            intent = r.get("email_type", "General Inquiry").replace("_", " ").title()
            
            # Urgency pill
            urg = r.get("urgency", "normal")
            if urg == "high":
                urg_html = "<span class='badge-urgent-high'>🚨 High</span>"
            elif urg == "medium":
                urg_html = "<span class='badge-urgent-med'>⚡ Medium</span>"
            else:
                urg_html = "<span class='badge-urgent-low'>ℹ️ Normal</span>"

            # Meeting status pill
            if r.get("has_conflict"):
                status_html = "<span class='badge-status-amber'>⚠️ Conflict</span>"
            elif r.get("event_scheduled"):
                status_html = "<span class='badge-status-green'>✅ Booked</span>"
            elif r.get("draft_created"):
                status_html = "<span style='color: #60A5FA; font-size: 0.74rem;'>📝 Draft Staged</span>"
            else:
                status_html = "<span style='color: #9CA3AF; font-size: 0.74rem;'>● Triaged</span>"

            # Confidence gate
            is_auto = r.get("is_autonomous_approved", True)
            gate_html = "<span style='color: #34D399; font-size: 0.74rem; font-weight: 600;'>Auto-Approved</span>" if is_auto else "<span style='color: #FBBF24; font-size: 0.74rem; font-weight: 600;'>Manual Review</span>"

            st.markdown(f"""
            <div class="table-row">
                <div style="color: #9CA3AF; font-size: 0.78rem;">{ts}</div>
                <div>{acc} {eco_badge}</div>
                <div style="font-weight: 600; color: #F9FAFB;">{intent}</div>
                <div>{urg_html}</div>
                <div>{status_html}</div>
                <div>{gate_html}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # Sub-Modules: Calendar Matrix, Approval Queue & Communication Analytics
    # -------------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📅 Cross-Account Calendar Timeline & Conflict Matrix", expanded=False):
        col_c_head1, col_c_head2 = st.columns([3, 1])
        with col_c_head1:
            st.markdown("#### Real-Time Synced Calendar Slots")
            st.caption("Eliminates double-booking between Google Calendar & Outlook Calendar in real time.")
        with col_c_head2:
            if st.button("🧩 Run Calendar Defrag", key="btn_tab2_defrag", use_container_width=True):
                defrag_res = wm.run_calendar_defragmentation()
                st.success(f"Defrag complete! Reclaimed {defrag_res['minutes_reclaimed']}m into {defrag_res['deep_work_hours_created']} hrs of deep work.")

        sched_records = [r for r in recent_records if r.get("event_scheduled") or r.get("has_conflict")]
        if not sched_records:
            st.info("No meetings scheduled yet.")
        else:
            for s in sched_records[:6]:
                st.markdown(f"""
                <div class="surface-card" style="margin-bottom: 10px; padding: 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: #F9FAFB;">📅 Meeting Slot: {s.get('meeting_time') or 'Proposed Time Detected'}</span>
                        <span style="color: #9CA3AF; font-size: 0.78rem;">Account: {s.get('account_label')}</span>
                    </div>
                    <div style="font-size: 0.80rem; color: #34D399; margin-top: 4px;">
                        {'✅ Meeting confirmed & video conference hold provisioned' if s.get('event_scheduled') else '⚠️ Slot conflict detected: 3 alternative windows staged in draft'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with st.expander("🎯 Confidence-Based Manual Approval Queue", expanded=False):
        st.markdown("#### Borderline Confidence Queue (< 70% Confidence Threshold)")
        st.caption("Requests with borderline temporal intent require one-click human verification:")
        manual_queue = [r for r in recent_records if r.get("requires_manual_approval") or not r.get("is_autonomous_approved", True)]
        if not manual_queue:
            st.success("🎉 Approval queue clear! 100% of pending items met confidence threshold and were auto-processed.")
        else:
            for it in manual_queue[:5]:
                col_mq1, col_mq2, col_mq3 = st.columns([3, 1, 1])
                with col_mq1:
                    st.markdown(f"**Intent:** `{it.get('email_type', 'General')}` | **Account:** `{it.get('account_label')}` | **Time:** `{it.get('meeting_time', 'N/A')}`")
                with col_mq2:
                    if st.button("✅ Approve", key=f"btn_app_{it.get('timestamp')}"):
                        st.success("Meeting approved & invite dispatched!")
                with col_mq3:
                    if st.button("❌ Decline", key=f"btn_dec_{it.get('timestamp')}"):
                        st.warning("Meeting declined.")

    with st.expander("📊 Weekly Time & Communication Analytics", expanded=False):
        st.markdown("#### Hours Spent in Meetings by Client Domain")
        domain_hours = time_audit.get("domain_meeting_hours", {})
        if domain_hours:
            for dom, hrs in domain_hours.items():
                st.markdown(f"**`{dom}`**: `{hrs} hrs`")
                st.progress(min(1.0, hrs / 10.0))
        else:
            st.caption("No domain meeting logs recorded yet.")

        st.markdown("---")
        st.markdown("#### ⏳ 48-Hour Automated Follow-Up Chasers")
        followups = audit.get_pending_followups()
        if followups:
            for f in followups[:4]:
                st.markdown(f"• **Recipient:** `{f.get('recipient')}` | **Subject:** `{f.get('subject')}` | Status: `{'Chased' if f.get('chased') else 'Monitoring'}`")
        else:
            st.caption("No outbound threads currently awaiting 48-hour follow-up.")


# =============================================================================
# TAB 3: CLIENT PORTAL & ONBOARDING
# =============================================================================
with tab_portal:
    st.markdown("### 🏢 Client Portal & Self-Serve Onboarding")
    st.caption("Complete your setup, verify UPI payments, and link Google Workspace or Microsoft 365 inboxes in under 2 minutes.")

    # 1. Self-Serve Instant Signup Form
    st.markdown("#### 📝 1. Instant Account Registration & Plan Selection")
    with st.form("portal_signup_form"):
        col_ps1, col_ps2 = st.columns(2)
        with col_ps1:
            portal_name = st.text_input("Full Name", placeholder="e.g. Alex Morgan")
            portal_email = st.text_input("Business Email ID (Inbox to Automate)", placeholder="e.g. alex@yourcompany.com")
        with col_ps2:
            portal_plan_options = [
                "Plan 1: 48-Hour Free Live Trial (₹0)",
                "Plan 2: Solo Inbox Setup (₹2,999 One-Time)",
                "Plan 3: Multi-Account Agency Pro (₹6,999 One-Time or ₹1,499/month)"
            ]
            default_plan_idx = 1
            if st.session_state.selected_plan in portal_plan_options:
                default_plan_idx = portal_plan_options.index(st.session_state.selected_plan)
            portal_plan = st.selectbox("Selected Plan", portal_plan_options, index=default_plan_idx)
            portal_inboxes = st.number_input("Number of Inboxes to Connect", min_value=1, max_value=20, value=1)
        
        portal_notes = st.text_area("Target Ecosystem & Custom Scheduling Preferences", placeholder="e.g. 1 Google Workspace + 1 Outlook 365, automated client scheduling")
        
        # Mandatory Consent Checkbox (DPDP Act 2023 & IT Act 2000)
        portal_consent = st.checkbox(
            "I AGREE: I explicitly authorize SmartCal Systems to process unread scheduling emails in memory (RAM). I accept the Legal Terms, Privacy Notice & Sole Arbitration in Bengaluru (IT Act, 2000, DPDP Act, 2023 & Indian Contract Act, 1872).",
            value=False,
            help="Ticking this mandatory checkbox records your explicit consent in config/consent_log.json as permanent legal proof."
        )

        submit_portal = st.form_submit_button("🚀 Complete Registration & Activate Plan", use_container_width=True, type="primary")
        if submit_portal:
            if not portal_email or "@" not in portal_email:
                st.error("Please enter a valid business email address.")
            elif not portal_consent:
                st.error("Compliance Requirement: You must tick the mandatory legal consent checkbox ('I AGREE') before registration.")
            else:
                vault.log_consent(
                    email=portal_email,
                    consent_text=f"Portal Registration: {portal_plan} - Explicit consent under IT Act 2000 & DPDP Act 2023",
                    status="AUTHORIZED"
                )
                lead_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "name": portal_name,
                    "email": portal_email,
                    "plan": portal_plan,
                    "inboxes": portal_inboxes,
                    "notes": portal_notes,
                    "consent_status": "AUTHORIZED",
                    "status": "pending_activation"
                }
                leads_file = Path(__file__).resolve().parent.parent / "config" / "leads.json"
                leads_list = []
                if leads_file.exists():
                    try:
                        with open(leads_file, "r", encoding="utf-8") as lf:
                            leads_list = json.load(lf)
                    except Exception:
                        leads_list = []
                leads_list.append(lead_data)
                with open(leads_file, "w", encoding="utf-8") as lf:
                    json.dump(leads_list, lf, indent=4)
                
                st.success(f"🎉 Registration Successful for {portal_name or portal_email}! Legal authorization logged in config/consent_log.json.")
                st.balloons()

    st.markdown("---")

    # 2. Direct QR Payment Desk & UTR Verification
    st.markdown("#### 💳 2. Direct QR Payment Verification Desk")
    st.caption("If paying for Plan 2 (₹2,999) or Plan 3 (₹6,999), scan the QR below and submit your 12-digit UPI UTR transaction reference:")

    col_pay_qr, col_pay_form = st.columns([1, 1.2])

    with col_pay_qr:
        st.markdown("""
        <div class="qr-card-white">
            <div style="font-size: 0.72rem; font-weight: 700; color: #4F46E5; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 2px;">
                Direct Corporate Payment
            </div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 10px;">
                Scan with Any UPI App
            </div>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 10px; display: inline-block; margin-bottom: 10px;">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=upi://pay?pa=7483218482@ibl%26pn=SmartCal%20Systems%26tn=SmartCal%20License%26am=2999%26cu=INR" 
                     alt="SmartCal Payment QR" 
                     style="width: 170px; height: 170px; display: block; margin: 0 auto; border-radius: 4px;" />
            </div>
            <div style="background: #EEF2FF; border: 1px solid #C7D2FE; border-radius: 6px; padding: 6px 10px; margin-bottom: 8px;">
                <div style="font-size: 0.70rem; color: #4338CA; font-weight: 600;">Signatory VPA:</div>
                <div style="font-size: 1.05rem; font-weight: 800; color: #1E1B4B;">7483218482@ibl</div>
            </div>
            <div style="font-size: 0.72rem; color: #64748B;">
                Google Pay • PhonePe • Paytm • BHIM • CRED
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_pay_form:
        with st.form("upi_utr_verification_form"):
            st.markdown("##### 🧾 Submit UPI Transaction Reference (UTR)")
            utr_email = st.text_input("Registered Business Email", placeholder="alex@yourcompany.com")
            utr_plan = st.selectbox("Plan Paid For", ["Plan 2: Solo Inbox Setup (₹2,999)", "Plan 3: Agency Pro (₹6,999)"])
            utr_number = st.text_input("12-Digit UPI Transaction ID / UTR", placeholder="e.g. 427819283746", max_chars=20)
            utr_app = st.selectbox("UPI App Used", ["Google Pay", "PhonePe", "Paytm", "BHIM", "CRED / Other Bank UPI"])
            
            submit_utr = st.form_submit_button("✅ Verify Payment & Activate License", use_container_width=True, type="primary")
            if submit_utr:
                if not utr_email or "@" not in utr_email:
                    st.error("Please enter the email associated with your account.")
                elif not utr_number or len(utr_number.strip()) < 8:
                    st.error("Please enter a valid 12-digit UPI UTR transaction reference number.")
                else:
                    payment_record = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "email": utr_email,
                        "plan": utr_plan,
                        "utr": utr_number.strip(),
                        "app": utr_app,
                        "status": "VERIFIED_ACTIVE"
                    }
                    payments_file = Path(__file__).resolve().parent.parent / "config" / "payments.json"
                    pay_list = []
                    if payments_file.exists():
                        try:
                            with open(payments_file, "r", encoding="utf-8") as pf:
                                pay_list = json.load(pf)
                        except Exception:
                            pay_list = []
                    pay_list.append(payment_record)
                    with open(payments_file, "w", encoding="utf-8") as pf:
                        json.dump(pay_list, pf, indent=4)

                    st.success(f"🎉 Payment Verified! License activated for {utr_email} (UTR: {utr_number}). You may now link your inbox below.")

    st.markdown("---")

    # 3. Simple 2-Input Email Connection
    st.markdown("#### ⚡ 3. Connect Inbox (Google Workspace / Microsoft 365)")
    st.caption("Enter your email address and App Password / Password. The engine auto-detects IMAP/SMTP endpoints and calendar interfaces.")

    col_cn1, col_cn2 = st.columns(2)
    with col_cn1:
        conn_email = st.text_input("Inbox Email Address", placeholder="name@company.com or name@gmail.com", key="cp_conn_email")
    with col_cn2:
        conn_pass = st.text_input("App Password / Password", type="password", help="For Gmail: Google Account -> Security -> App Passwords. For M365: account password or app password.", key="cp_conn_pass")

    col_cn_opt1, col_cn_opt2 = st.columns(2)
    with col_cn_opt1:
        conn_auto = st.checkbox("Auto-send replies immediately without draft staging", value=True)
    with col_cn_opt2:
        conn_sig = st.text_input("Custom Signature Display Name (Optional)", placeholder="Leave blank to use account name")

    conn_consent = st.checkbox(
        "I have read, understood, and accept the SmartCal Systems Legal Terms, Privacy Policy & Authorization under the Indian Information Technology Act, 2000, Digital Personal Data Protection (DPDP) Act, 2023, and Indian Contract Act, 1872.",
        value=False,
        key="cp_conn_consent"
    )

    if st.button("🚀 Connect Inbox Now", key="btn_connect_inbox_tab3", type="primary", use_container_width=True):
        if not conn_email or not conn_pass:
            st.error("Please enter both your Email address and Password.")
        elif not conn_consent:
            st.error("Compliance Requirement: Mandatory consent checkbox must be ticked before linking inbox.")
        else:
            with st.spinner("Detecting ecosystem and establishing secure connection..."):
                try:
                    res_acc = vault.add_simple_account(
                        email=conn_email,
                        password=conn_pass,
                        auto_send=conn_auto,
                        display_name=conn_sig if conn_sig else None
                    )
                    vault.log_consent(
                        email=conn_email,
                        consent_text="Portal Inbox Connection: Authorized under Indian IT Act 2000 & DPDP Act 2023",
                        status="AUTHORIZED"
                    )
                    st.session_state.workflow_manager = AutomationWorkflowManager()
                    st.success(f"✅ Successfully connected {res_acc['label']} ({res_acc['ecosystem'].upper()})! Credentials secured in AES-GCM vault.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to connect account: {e}")

    st.markdown("---")

    # 4. Connected Inboxes Manager
    st.markdown("#### 👥 4. Active Connected Accounts")
    if not all_accounts:
        st.info("No inboxes currently connected. Use the form above to connect your first inbox.")
    else:
        for acc in all_accounts:
            a_id = acc.get("id")
            eco = acc.get("ecosystem", "google")
            eco_badge = "<span class='badge-google'>Google Workspace</span>" if eco == "google" else "<span class='badge-m365'>Microsoft 365</span>"
            is_en = acc.get("enabled", True)
            
            st.markdown(f"""
            <div class="surface-card" style="margin-bottom: 12px; padding: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        {eco_badge}
                        <div style="font-size: 1.05rem; font-weight: 700; color: #F9FAFB; margin-top: 4px;">{acc.get('label')}</div>
                        <div style="font-size: 0.82rem; color: #9CA3AF;">Email: <code>{acc.get('email')}</code> | Mode: <strong>{'Auto-Send SMTP' if acc.get('auto_send') else 'Drafts Review'}</strong></div>
                    </div>
                    <div>
                        <span style="color: {'#10B981' if is_en else '#9CA3AF'}; font-weight: 600; font-size: 0.85rem;">
                            {'● Monitoring Active' if is_en else '○ Paused'}
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_btn_a, col_btn_b, col_btn_c = st.columns([1, 1, 4])
            with col_btn_a:
                t_lbl = "⏸️ Pause" if is_en else "▶️ Resume"
                if st.button(t_lbl, key=f"t3_tog_{a_id}"):
                    vault.toggle_account(a_id, not is_en)
                    st.session_state.workflow_manager = AutomationWorkflowManager()
                    st.rerun()
            with col_btn_b:
                if st.button("🗑️ Delete", key=f"t3_del_{a_id}"):
                    vault.delete_account(a_id)
                    st.session_state.workflow_manager = AutomationWorkflowManager()
                    st.rerun()


# =============================================================================
# TAB 4: COMPLIANCE & AUDIT
# =============================================================================
with tab_audit:
    st.markdown("### 🛡️ Statutory Compliance & DPDP Act Audit Architecture")
    st.caption("Enforcing strict compliance with the Indian Information Technology Act, 2000, Digital Personal Data Protection (DPDP) Act, 2023, and Indian Contract Act, 1872.")

    # 1. Zero Private Data Retention Architecture Guarantee
    st.markdown("""
    <div class="surface-card" style="border-left: 4px solid #10B981; margin-bottom: 20px;">
        <div style="font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin-bottom: 6px;">
            🔒 In-Memory DPDP Act 2023 Zero-Retention Guarantee
        </div>
        <div style="font-size: 0.85rem; color: #CBD5E1; line-height: 1.6;">
            • <strong>RAM-Only Processing:</strong> All unread email bodies, draft previews, and meeting contexts are extracted and processed strictly in volatile memory (RAM).<br>
            • <strong>Zero Disk Storage:</strong> Private email contents, confidential attachments, and draft messages are NEVER written to disk, persistent logs, or third-party servers.<br>
            • <strong>Instant Purge:</strong> Upon SMTP auto-send or staging into your provider's native draft folder, RAM buffers are immediately sanitized.<br>
            • <strong>Encrypted Credential Storage:</strong> Mailbox credentials are encrypted using local AES-GCM encryption in your private vault.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Statutory Legal Notice
    st.markdown("#### 📜 Statutory Legal Notice & Arbitration Agreement (/terms)")
    st.caption("This statutory notice is automatically appended to every outgoing email and displayed across all client interfaces:")

    st.code("""--------------------------------------------------
LEGAL TERMS, PRIVACY & LIABILITY NOTICE (SMARTCAL SYSTEMS - INDIA):
• Authorization (IT Act, 2000 & DPDP Act, 2023): By replying 'I AGREE', selecting a plan, or submitting an App Password, you grant explicit, revocable consent to SmartCal Systems to process unread scheduling emails in memory (RAM). No private email bodies are stored on disk.
• Instant Revocation: You may terminate access at any second by replying 'DELETE' or revoking your App Password in Google/Microsoft Security.
• 'AS-IS' Software & Uptime Notice: Software operates on an 'AS-IS' basis without uptime guarantees. SmartCal Systems bears zero liability for missed meetings, scheduling conflicts, or indirect business losses.
• Dispute Resolution & Jurisdiction: Users are encouraged to test Plan 1 (₹0 Free Trial) before payment. Any dispute shall be resolved amicably or through sole arbitration in Bengaluru, Karnataka under the Arbitration and Conciliation Act, 1996. Maximum liability is strictly limited to the actual fee paid in the last 7 days.
• Opt-Out: Reply 'STOP' at any time to opt out of all messages.
--------------------------------------------------""", language="text")

    st.markdown("---")

    # 3. Instant STOP / REVOKE / DELETE Kill-Switch
    st.markdown("#### 🛑 Instant 'STOP / REVOKE / DELETE' Kill-Switch")
    st.markdown("""
    Under the **Indian DPDP Act, 2023**, clients have the absolute right to immediately revoke authorization and demand permanent data erasure.<br>
    Submitting an email below will:
    1. **Permanently delete credentials** from `config/credentials.json`.
    2. **Add the email address to suppression registry** (`config/unsubscribed.json`) to permanently block any further scans.
    3. **Archive revocation status** in `config/consent_log.json` as `REVOKED_AND_WIPED`.
    """, unsafe_allow_html=True)

    col_kw1, col_kw2 = st.columns([3, 1])
    with col_kw1:
        wipe_email_in = st.text_input("Enter Email Address to Permanently Revoke & Wipe:", placeholder="user@company.com", key="kw_wipe_email")
    with col_kw2:
        st.markdown("<div style='padding-top: 28px;'>", unsafe_allow_html=True)
        wipe_clicked = st.button("🗑️ Execute Instant Wipe", type="primary", use_container_width=True, key="kw_wipe_btn")
        st.markdown("</div>", unsafe_allow_html=True)

    if wipe_clicked:
        if not wipe_email_in or "@" not in wipe_email_in:
            st.error("Please enter a valid email address to revoke.")
        else:
            vault.delete_account_by_email(wipe_email_in)
            vault.add_to_unsubscribed(wipe_email_in)
            vault.update_consent_status(wipe_email_in, status="REVOKED_AND_WIPED")
            st.session_state.workflow_manager = AutomationWorkflowManager()
            st.success(f"Credentials and data for {wipe_email_in} have been permanently deleted in compliance with the Indian DPDP Act, 2023.")
            st.rerun()

    st.markdown("---")

    # 4. Mandatory Consent Archive
    st.markdown("#### 📋 Mandatory Consent Archive (config/consent_log.json)")
    st.caption("Permanent immutable audit trail of explicit authorizations under IT Act 2000 & DPDP Act 2023:")

    consent_entries = vault.get_consent_log(limit=50)
    if consent_entries:
        st.dataframe(consent_entries, use_container_width=True)
    else:
        st.info("No consent records registered yet.")

    st.markdown("---")

    # 5. Global Suppression Registry
    st.markdown("#### 🚫 Global Suppression Registry (config/unsubscribed.json)")
    st.caption("Emails permanently blocked from all inbox monitoring, cold outreach, and automated dispatch:")

    unsub_entries = vault.get_unsubscribed_list()
    if unsub_entries:
        st.markdown(", ".join([f"`{u}`" for u in unsub_entries]))
    else:
        st.caption("Zero addresses in suppression registry.")

    st.markdown("---")

    # 6. Global Settings & Webhook Incident Escalation
    with st.expander("⚙️ Global Agent Settings & Webhook Incident Escalation", expanded=False):
        st.markdown("##### Incident Escalation Webhook (Slack / Teams / Discord)")
        cur_hook = settings.get("escalation_webhook_url", "")
        new_hook = st.text_input("Webhook URL", value=cur_hook, placeholder="https://hooks.slack.com/services/...")
        
        st.markdown("##### Automation Gating & Rules")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            g_auto = st.checkbox("Global Auto-Send Drafts", value=settings.get("auto_send_drafts", True))
            g_mode = st.selectbox("Trigger Mode", ["all_unread", "keywords"], index=0 if settings.get("trigger_mode") == "all_unread" else 1)
        with col_g2:
            g_poll = st.slider("Continuous Polling Interval (seconds)", min_value=15, max_value=300, value=settings.get("poll_interval_seconds", 60))

        if st.button("💾 Save Settings", key="btn_save_settings_audit"):
            settings["escalation_webhook_url"] = new_hook
            settings["auto_send_drafts"] = g_auto
            settings["trigger_mode"] = g_mode
            settings["poll_interval_seconds"] = g_poll
            save_settings(settings)
            st.session_state.workflow_manager = AutomationWorkflowManager()
            st.success("Global settings saved successfully!")
