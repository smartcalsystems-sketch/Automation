"""Master CLI Entrypoint for SmartCal Systems Autonomous Email & Calendar Automation Agent.

Supports Multi-Account Google Workspace and Microsoft 365 scanning, management, and auto-advertising.
"""
import argparse
import sys
import time
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List

# Ensure UTF-8 stdout encoding on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console  # type: ignore
from rich.table import Table  # type: ignore
from rich.panel import Panel  # type: ignore

from config.settings import load_settings
from pipeline.workflow_manager import AutomationWorkflowManager
from auth.vault import CredentialVault
from engine.email_drafter import LEGAL_NOTICE_FOOTER

console = Console(highlight=False)


def print_banner():
    banner_text = """[bold cyan]SMARTCAL SYSTEMS - AUTONOMOUS INBOX & CALENDAR ENGINE[/bold cyan]
[dim]Intelligent Email & Calendar Automation across Multiple Google Workspace & Microsoft 365 Accounts[/dim]"""
    console.print(Panel(banner_text, border_style="cyan"))


def send_promotional_advertisement(target_emails: List[str]):
    """Send cold promotional pitch emails from smartcal.systems@gmail.com pitching SmartCal Systems."""
    vault = CredentialVault()
    accounts = vault.list_accounts(enabled_only=True)
    sender_account = None
    for acc in accounts:
        if acc.get("email") == "smartcal.systems@gmail.com":
            sender_account = acc
            break
    if not sender_account and accounts:
        sender_account = accounts[0]

    if not sender_account or not sender_account.get("app_password"):
        console.print("[bold red]Error: No configured account found with valid App Password in vault.[/bold red]")
        return

    sender_email = sender_account["email"]
    app_password = sender_account["app_password"]
    subject = "🚀 24/7 Inbox-to-Calendar Automation in 60 Seconds — SmartCal Systems Demo"
    
    pitch_body = f"""Hi there,

Tired of manually managing scheduling emails, calendar conflicts, and missing client replies?

SmartCal Systems is an autonomous email triage and calendar scheduling engine that turns every inbound inquiry into a booked Google Meet or Microsoft Teams meeting in under 60 seconds.

🚀 How SmartCal Systems Works (24/7 Inbox-to-Calendar Automation in 60 Seconds):
  • 60-Second Email Triage: Automatically reads, categorizes, and logs incoming client emails and deliverables with zero latency.
  • Autonomous Calendar Booking: Resolves scheduling conflicts across Google & Outlook calendars and provisions Google Meet / Teams links instantly.
  • 24/7 Follow-Up Loops: Staged 48-hour follow-up chasers, automated Minutes of Meeting (MoM), and live no-show recovery.

💼 Transparent Pricing Plans:
  • Plan 1: 48-Hour Free Live Trial (₹0)
  • Plan 2: Solo Inbox Setup (₹2,999 One-Time)
  • Plan 3: Multi-Account Agency Pro — Up to 5 Inboxes + Follow-Up Chasers + Invoice Reminders (₹6,999 One-Time or ₹1,499/month)

👉 Want to see it in action?
Reply to this email with "DEMO" to test our live AI engine in 60 seconds, or reply with "PLAN 1", "PLAN 2", or "PLAN 3" to activate SmartCal on your inbox today!

Best regards,
SmartCal Systems
Automated Email & Calendar Scheduling Engine

{LEGAL_NOTICE_FOOTER}"""

    console.print(f"[bold cyan]Dispatched SmartCal Promotional Campaign from {sender_email} to {len(target_emails)} recipients...[/bold cyan]\n")

    results_table = Table(title="Cold Outreach Dispatch Log")
    results_table.add_column("Recipient", style="cyan")
    results_table.add_column("Status", style="bold")
    results_table.add_column("Timestamp", style="white")

    for target in target_emails:
        target = target.strip()
        if not target or "@" not in target:
            results_table.add_row(target, "[yellow]SKIPPED (Invalid)[/yellow]", datetime.utcnow().strftime("%H:%M:%S"))
            continue

        # Check unsubscribed list (DPDP Act Compliance)
        if vault.is_unsubscribed(target):
            results_table.add_row(target, "[yellow]SKIPPED (Unsubscribed / Opted-Out)[/yellow]", datetime.utcnow().strftime("%H:%M:%S"))
            continue

        try:
            msg = MIMEMultipart()
            msg["From"] = f"SmartCal Systems <{sender_email}>"
            msg["To"] = target
            msg["Subject"] = subject
            msg.attach(MIMEText(pitch_body, "plain"))

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, [target], msg.as_string())
            server.quit()
            results_table.add_row(target, "[green]SENT (SMTP)[/green]", datetime.utcnow().strftime("%H:%M:%S"))
        except Exception as e:
            results_table.add_row(target, f"[red]FAILED: {str(e)[:40]}[/red]", datetime.utcnow().strftime("%H:%M:%S"))

    console.print(results_table)


def run_diagnostics(wm: AutomationWorkflowManager):
    console.print("[bold yellow]Running Multi-Account Diagnostics & Reachability...[/bold yellow]")
    results = wm.run_health_check()

    table = Table(title="Connected Accounts & Service Reachability")
    table.add_column("Account Label", style="cyan", no_wrap=True)
    table.add_column("Ecosystem", style="magenta")
    table.add_column("Email / Target", style="blue")
    table.add_column("Status", style="bold")
    table.add_column("Diagnostics", style="white")

    for acc_id, res in results.items():
        eco = str(res.get("ecosystem", "")).upper()
        email_str = res.get("email") or "N/A"
        label = res.get("label", acc_id)
        status = "[green]ONLINE / CONNECTED[/green]" if res.get("success") else "[yellow]SANDBOX / SIMULATED[/yellow]"
        details = res.get("message", "")
        table.add_row(label, eco, email_str, status, details)

    console.print(table)


def run_scan_cycle(wm: AutomationWorkflowManager, target_account: str = None, is_demo: bool = False):
    acc_msg = f"Target Account: {target_account}" if target_account else "All Configured Accounts"
    console.print(f"\n[bold green]Initiating Multi-Account Scanning Cycle ({'SIMULATION' if is_demo else 'ACTIVE'} - {acc_msg})...[/bold green]")
    res = wm.process_all_ecosystems(target_account_id=target_account)

    summary_table = Table(title="Workflow Execution Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="bold green")

    summary_table.add_row("Accounts Monitored", str(res["accounts_scanned"]))
    summary_table.add_row("Total Inboxes Scanned", str(res["emails_scanned"]))
    summary_table.add_row("Total Emails Processed", str(res["emails_processed"]))
    summary_table.add_row("Calendar Invites Booked", str(res["events_scheduled"]))
    summary_table.add_row("Contextual Replies Auto-Sent", str(res["drafts_created"]))
    summary_table.add_row("Cross-Account Conflicts Handled", str(res["conflicts_detected"]))
    summary_table.add_row("Emergency Focus Escalations", str(res.get("escalations_triggered", 0)))
    summary_table.add_row("Task Focus/Prep Blocks", str(res.get("focus_blocks_scheduled", 0)))
    summary_table.add_row("Invoices & Payment Reminders", str(res.get("invoices_extracted", 0)))
    summary_table.add_row("OOO Auto-Rescheduled", str(res.get("ooo_rescheduled", 0)))
    summary_table.add_row("Pre-Meeting Dossiers Attached", str(res.get("dossiers_attached", 0)))
    summary_table.add_row("48h No-Reply Chasers Staged", str(res.get("followups_chased", 0)))
    console.print(summary_table)

    if res["items"]:
        console.print("\n[bold]Processed Messages & Multi-Account Actions:[/bold]")
        items_table = Table()
        items_table.add_column("Account", style="cyan")
        items_table.add_column("Platform", style="magenta")
        items_table.add_column("Sender", style="blue")
        items_table.add_column("Subject", style="white")
        items_table.add_column("Scheduled Slot", style="yellow")
        items_table.add_column("Meeting Link", style="green")
        items_table.add_column("Status", style="bold")

        for it in res["items"]:
            if it.get("skipped"):
                items_table.add_row(
                    it.get("account_label", "")[:20],
                    it.get("ecosystem", "").upper(),
                    it.get("sender", ""),
                    it.get("subject", "")[:30] + "...",
                    "N/A",
                    "N/A",
                    "[dim yellow]🚫 Blocked System / Bot[/dim yellow]"
                )
                continue

            cal = it.get("calendar_result") or {}
            link = cal.get("meeting_link", "N/A")
            slot = it.get("proposed_datetime") or "N/A"
            if it.get("has_conflict"):
                status = "[red]Conflict (Rescheduled)[/red]"
            elif it.get("escalation_triggered"):
                status = "[bold red]🚨 Escalated & Focus Blocked[/bold red]"
            elif it.get("invoice_extracted"):
                status = "[cyan]💳 Invoice & Reminder Booked[/cyan]"
            elif it.get("focus_blocks_scheduled"):
                status = "[blue]🎯 Task Focus Time-Blocked[/blue]"
            elif it.get("ooo_rescheduled"):
                status = "[yellow]🏖️ OOO Rescheduled[/yellow]"
            elif it.get("event_scheduled"):
                status = "[green]📅 Booked & Auto-Sent[/green]"
            else:
                status = "[dim green]✉️ Auto-Sent via SMTP[/dim green]"
            items_table.add_row(
                it.get("account_label", "")[:20],
                it.get("ecosystem", "").upper(),
                it.get("sender", ""),
                it.get("subject", "")[:30] + "...",
                slot,
                link,
                status
            )
        console.print(items_table)


def run_continuous_daemon(wm: AutomationWorkflowManager, target_account: str = None, interval: int = 60):
    console.print(f"[bold green]Starting Autonomous Multi-Account Daemon (Polling every {interval}s)...[/bold green]")
    console.print("[dim]Press Ctrl+C to terminate.[/dim]\n")
    try:
        while True:
            console.print(f"\n[bold cyan]Cycle Trigger: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}[/bold cyan]")
            run_scan_cycle(wm, target_account=target_account)
            console.print(f"[dim]Sleeping for {interval} seconds...[/dim]")
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[bold red]Daemon stopped by user.[/bold red]")


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="SmartCal Systems Multi-Account Email & Calendar Agent")
    parser.add_argument("--scan", action="store_true", help="Execute an immediate multi-account scan and processing run")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background polling mode")
    parser.add_argument("--check", action="store_true", help="Run system diagnostics across all accounts")
    parser.add_argument("--demo", action="store_true", help="Execute simulation run with sample enterprise emails")
    parser.add_argument("--dashboard", action="store_true", help="Launch the Streamlit Web Control Center")
    parser.add_argument("--advertise", nargs="+", metavar="EMAIL", help="Send cold promotional emails pitching SmartCal Systems to target email addresses")
    parser.add_argument("--account", type=str, default=None, help="Specific Account ID to scan (default: all accounts)")
    parser.add_argument("--add-account", nargs=2, metavar=("EMAIL", "PASSWORD"), help="Connect an account with just Email and Password")
    parser.add_argument("--interval", type=int, default=None, help="Daemon polling interval in seconds")

    args = parser.parse_args()
    settings = load_settings()
    interval = args.interval or settings.get("poll_interval_seconds", 60)

    if args.advertise:
        send_promotional_advertisement(args.advertise)
        return

    if args.add_account:
        from auth.vault import CredentialVault
        vault = CredentialVault()
        email_arg, pass_arg = args.add_account
        console.print(f"[bold cyan]Auto-detecting ecosystem and registering {email_arg}...[/bold cyan]")
        try:
            res = vault.add_simple_account(email=email_arg, password=pass_arg)
            vault.log_consent(
                email=email_arg,
                consent_text="CLI Registration: Authorized SmartCal Systems email monitoring & scheduling under Indian IT Act 2000 & DPDP Act 2023",
                status="AUTHORIZED"
            )
            console.print(f"[bold green]Successfully connected account and logged legal consent archive![/bold green]")
            console.print(f"  • Platform: [bold magenta]{res['ecosystem'].upper()}[/bold magenta]")
            console.print(f"  • Account Label: {res['label']}")
            console.print(f"  • Meeting Engine: {'Google Meet' if res['ecosystem'] == 'google' else 'Microsoft Teams'}")
            console.print(f"  • Calendar: {'Google Calendar' if res['ecosystem'] == 'google' else 'Outlook Calendar'}")
            console.print(f"[dim]Run 'python main.py --scan' to begin monitoring.[/dim]")
        except Exception as e:
            console.print(f"[bold red]Failed to register account: {e}[/bold red]")
        return

    if args.dashboard:
        import subprocess
        console.print("[bold green]Launching Multi-Account Streamlit Dashboard on http://localhost:8501...[/bold green]")
        subprocess.run(["streamlit", "run", "ui/dashboard.py"])
        return

    wm = AutomationWorkflowManager(force_simulation=args.demo)

    if args.check:
        run_diagnostics(wm)
    elif args.daemon:
        run_continuous_daemon(wm, target_account=args.account, interval=interval)
    elif args.scan or args.demo:
        run_scan_cycle(wm, target_account=args.account, is_demo=args.demo)
    else:
        # Default action: Diagnostic check followed by a scan cycle
        run_diagnostics(wm)
        run_scan_cycle(wm, target_account=args.account, is_demo=False)


if __name__ == "__main__":
    main()
