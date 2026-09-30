"""Autonomous Email Provider & Ecosystem Detection.

Allows users to simply provide an Email and Password. The agent automatically detects
whether the account belongs to Google Workspace (Gmail) or Microsoft 365 (Outlook/Teams),
configures the connection, and sets up appropriate calendar/meeting providers.
"""
import re
import subprocess
import socket
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("AutomationAgent.Detector")

KNOWN_GOOGLE_DOMAINS = {
    "gmail.com", "googlemail.com", "google.com"
}

KNOWN_M365_DOMAINS = {
    "outlook.com", "hotmail.com", "live.com", "msn.com",
    "office365.com", "microsoft.com", "onmicrosoft.com"
}


def auto_detect_email_service(email_address: str) -> Dict[str, Any]:
    """Auto-detect ecosystem, label, servers, and meeting provider from email address alone."""
    email_clean = email_address.strip().lower()
    if "@" not in email_clean:
        raise ValueError(f"Invalid email format: {email_address}")

    user_part, domain = email_clean.split("@", 1)
    
    # 1. Check known domain maps
    if domain in KNOWN_GOOGLE_DOMAINS:
        ecosystem = "google"
    elif domain in KNOWN_M365_DOMAINS:
        ecosystem = "m365"
    else:
        # 2. Check MX record for custom enterprise/corporate domains
        ecosystem = _probe_mx_records(domain)

    # 3. Auto-generate human-readable label and display name
    clean_name = user_part.replace(".", " ").replace("_", " ").title()
    label = f"{clean_name} ({domain})"
    display_name = f"{clean_name} (SmartCal Systems)"

    if ecosystem == "google":
        return {
            "ecosystem": "google",
            "email": email_clean,
            "label": label,
            "display_name": display_name,
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "meeting_provider": "Google Meet",
            "calendar_service": "Google Calendar"
        }
    else:
        return {
            "ecosystem": "m365",
            "email": email_clean,
            "label": label,
            "display_name": display_name,
            "imap_server": "outlook.office365.com",
            "imap_port": 993,
            "smtp_server": "smtp.office365.com",
            "smtp_port": 587,
            "meeting_provider": "Microsoft Teams",
            "calendar_service": "Outlook Calendar"
        }


def _probe_mx_records(domain: str) -> str:
    """Inspect DNS MX records using Windows nslookup to detect Google vs Microsoft."""
    try:
        proc = subprocess.run(
            ["nslookup", "-type=mx", domain],
            capture_output=True,
            text=True,
            timeout=4
        )
        output = (proc.stdout or "").lower()

        # Google indicators
        if any(g in output for g in ["google", "aspmx", "googlemail", "smtp.google.com"]):
            logger.info(f"Domain {domain} MX records indicate Google Workspace.")
            return "google"

        # Microsoft indicators
        if any(m in output for m in ["outlook", "microsoft", "office365", "mail.protection.outlook.com"]):
            logger.info(f"Domain {domain} MX records indicate Microsoft 365.")
            return "m365"

    except Exception as e:
        logger.warning(f"MX probe for {domain} failed: {e}. Defaulting to Google Workspace.")

    # Default heuristic
    return "google" if "google" in domain else "m365"
