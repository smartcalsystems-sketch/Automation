"""Configuration settings and environment loading for Email & Calendar Automation Agent."""
import os
import json
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "settings.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
CONSENT_LOG_FILE = CONFIG_DIR / "consent_log.json"
UNSUBSCRIBED_FILE = CONFIG_DIR / "unsubscribed.json"
AUDIT_LOG_FILE = BASE_DIR / "automation_audit.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "ecosystem": "hybrid",  # "google", "m365", "hybrid"
    "auth_mode": "direct",  # "direct", "rdp", "hybrid"
    "trigger_mode": "all_unread",  # "all_unread", "keywords"
    "keywords": [
        "meeting", "schedule", "call", "sync", "demo", 
        "discuss", "interview", "catch up", "appointment", "calendar"
    ],
    "auto_send_drafts": True,  # Auto-send email replies via SMTP
    "poll_interval_seconds": 60,
    "default_meeting_duration_minutes": 45,
    "default_timezone": "IST",
    "google": {
        "enabled": True,
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "calendar_enabled": True
    },
    "m365": {
        "enabled": True,
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "calendar_enabled": True,
        "teams_integration": True
    },
    "rdp": {
        "enabled": False,
        "host": "127.0.0.1",
        "port": 3389,
        "browser_profile_dir": ""
    },
    "vip_senders": [
        "ceo@company.com",
        "board@venturecap.com",
        "sarah.jenkins@acmepartners.com"
    ],
    "vip_domains": [
        "acmepartners.com",
        "venturecap.com"
    ],
    "recipient_preferences": {},
    "role_routing": {
        "enabled": True,
        "executive_keywords": ["strategy", "board", "investor", "partnership", "confidential", "m&a", "advisory"],
        "operations_keywords": ["support", "bug", "ticket", "invoice", "billing", "access", "operational", "technical issue", "error", "incident", "dns", "provisioning"],
        "default_ops_email": "ops@company.internal",
        "default_ops_label": "Client Operations"
    },
    "circuit_breaker": {
        "enabled": True,
        "failure_threshold": 3,
        "cooldown_seconds": 300
    }
}


def load_settings() -> Dict[str, Any]:
    """Load settings from JSON file or return defaults."""
    if not CONFIG_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Merge with defaults for missing keys
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            return merged
    except Exception as e:
        print(f"Error loading {CONFIG_FILE}: {e}. Using defaults.")
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to settings.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)
