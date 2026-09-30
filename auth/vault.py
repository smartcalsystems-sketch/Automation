"""Secure Multi-Account Credential Vault for Google Workspace and Microsoft 365."""
import os
import json
import base64
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from Crypto.Cipher import AES  # type: ignore
    from Crypto.Protocol.KDF import PBKDF2  # type: ignore
    from Crypto.Random import get_random_bytes  # type: ignore
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from datetime import datetime
import pytz
from config.settings import CREDENTIALS_FILE, CONFIG_DIR, CONSENT_LOG_FILE, UNSUBSCRIBED_FILE

DEFAULT_VAULT: Dict[str, Any] = {
    "accounts": [],
    "rdp": {
        "host": "127.0.0.1",
        "port": 3389,
        "username": "",
        "password": "",
        "domain": "",
        "browser_path": ""
    }
}


class CredentialVault:
    """Manages multi-account credentials securely with local persistence and AES-GCM encryption."""

    def __init__(self, key: Optional[str] = None, vault_file: Optional[Path] = None):
        self.vault_file = vault_file or CREDENTIALS_FILE
        self.secret_key = (key or os.environ.get("SMARTCAL_VAULT_KEY") or "SmartCalSecret2026!").encode("utf-8")
        self._ensure_vault()

    def _ensure_vault(self) -> None:
        """Create empty credentials file if missing, or migrate older format."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not self.vault_file.exists():
            self._write_raw_vault(DEFAULT_VAULT)
        else:
            self._migrate_if_needed()

    def _encrypt(self, plaintext: str) -> str:
        """Obfuscation/encryption for local storage."""
        if not plaintext:
            return ""
        if CRYPTO_AVAILABLE:
            salt = get_random_bytes(16)
            key = PBKDF2(self.secret_key, salt, dkLen=32, count=1000)
            cipher = AES.new(key, AES.MODE_GCM)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
            packed = salt + cipher.nonce + tag + ciphertext
            return "ENC:" + base64.b64encode(packed).decode('utf-8')
        else:
            return "B64:" + base64.b64encode(plaintext.encode('utf-8')).decode('utf-8')

    def _decrypt(self, token: str) -> str:
        """Decrypt or decode stored token."""
        if not token:
            return ""
        try:
            if token.startswith("ENC:") and CRYPTO_AVAILABLE:
                raw = base64.b64decode(token[4:])
                salt = raw[:16]
                nonce = raw[16:32]
                tag = raw[32:48]
                ciphertext = raw[48:]
                key = PBKDF2(self.secret_key, salt, dkLen=32, count=1000)
                cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
            elif token.startswith("B64:"):
                return base64.b64decode(token[4:]).decode('utf-8')
            return token
        except Exception:
            return token

    def _read_raw_vault(self) -> Dict[str, Any]:
        try:
            with open(self.vault_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_VAULT.copy()

    def _write_raw_vault(self, data: Dict[str, Any]) -> None:
        with open(self.vault_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _migrate_if_needed(self) -> None:
        """Migrate legacy single-account vault format to multi-account list."""
        data = self._read_raw_vault()
        updated = False
        if "accounts" not in data:
            data["accounts"] = []
            updated = True

        # Check if legacy top-level "google" exists with email
        if "google" in data and isinstance(data["google"], dict):
            g_email = data["google"].get("email")
            if g_email and not any(a.get("email") == g_email for a in data["accounts"]):
                data["accounts"].append({
                    "id": f"acc_google_{uuid.uuid4().hex[:6]}",
                    "label": f"Google Workspace ({g_email})",
                    "ecosystem": "google",
                    "email": g_email,
                    "app_password": data["google"].get("app_password", ""),
                    "enabled": True,
                    "auto_send_drafts": False,
                    "display_name": "SmartCal Systems"
                })
                updated = True

        # Check if legacy top-level "m365" exists with email
        if "m365" in data and isinstance(data["m365"], dict):
            m_email = data["m365"].get("email")
            if m_email and not any(a.get("email") == m_email for a in data["accounts"]):
                data["accounts"].append({
                    "id": f"acc_m365_{uuid.uuid4().hex[:6]}",
                    "label": f"Microsoft 365 ({m_email})",
                    "ecosystem": "m365",
                    "email": m_email,
                    "password": data["m365"].get("password", ""),
                    "tenant_id": data["m365"].get("tenant_id", ""),
                    "enabled": True,
                    "auto_send_drafts": False,
                    "display_name": "SmartCal Systems"
                })
                updated = True

        if updated:
            self._write_raw_vault(data)

    def list_accounts(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List all accounts with decrypted credentials."""
        data = self._read_raw_vault()
        accounts = data.get("accounts", [])
        result = []
        for acc in accounts:
            if enabled_only and not acc.get("enabled", True):
                continue
            acc_copy = acc.copy()
            # Decrypt secrets
            for sec_key in ["app_password", "password", "client_secret"]:
                if sec_key in acc_copy and acc_copy[sec_key]:
                    acc_copy[sec_key] = self._decrypt(acc_copy[sec_key])
            result.append(acc_copy)
        return result

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific account by ID."""
        for acc in self.list_accounts():
            if acc.get("id") == account_id:
                return acc
        return None

    def add_simple_account(self, email: str, password: str, auto_send: bool = False, display_name: Optional[str] = None) -> Dict[str, Any]:
        """Auto-detect ecosystem and configure account using only email and password."""
        from auth.account_detector import auto_detect_email_service
        detected = auto_detect_email_service(email)
        acc_payload = {
            "id": f"acc_{detected['ecosystem']}_{uuid.uuid4().hex[:6]}",
            "label": detected["label"],
            "ecosystem": detected["ecosystem"],
            "email": detected["email"],
            "enabled": True,
            "display_name": display_name or detected["display_name"],
            "auto_send_drafts": auto_send
        }
        if detected["ecosystem"] == "google":
            acc_payload["app_password"] = password
        else:
            acc_payload["password"] = password

        self.upsert_account(acc_payload)
        return acc_payload

    def upsert_account(self, account_data: Dict[str, Any]) -> str:
        """Add or update an account configuration with encrypted secrets."""
        data = self._read_raw_vault()
        accounts: List[Dict[str, Any]] = data.get("accounts", [])

        acc_id = account_data.get("id") or f"acc_{account_data.get('ecosystem', 'acc')}_{uuid.uuid4().hex[:6]}"
        to_store = account_data.copy()
        to_store["id"] = acc_id

        # Encrypt secrets before saving
        for sec_key in ["app_password", "password", "client_secret"]:
            if sec_key in to_store and to_store[sec_key]:
                raw_val = to_store[sec_key]
                if not raw_val.startswith(("ENC:", "B64:")):
                    to_store[sec_key] = self._encrypt(raw_val)

        # Update if exists, else append
        existing_idx = next((i for i, a in enumerate(accounts) if a.get("id") == acc_id), -1)
        if existing_idx >= 0:
            accounts[existing_idx] = to_store
        else:
            accounts.append(to_store)

        data["accounts"] = accounts
        self._write_raw_vault(data)
        return acc_id

    def delete_account(self, account_id: str) -> bool:
        """Remove an account by ID."""
        data = self._read_raw_vault()
        original_len = len(data.get("accounts", []))
        data["accounts"] = [a for a in data.get("accounts", []) if a.get("id") != account_id]
        if len(data["accounts"]) < original_len:
            self._write_raw_vault(data)
            return True
        return False

    def delete_account_by_email(self, email: str) -> bool:
        """Immediately remove an account and credentials from vault by email address (DPDP Act Kill-Switch)."""
        if not email:
            return False
        clean_email = email.strip().lower()
        data = self._read_raw_vault()
        original_len = len(data.get("accounts", []))
        data["accounts"] = [
            a for a in data.get("accounts", [])
            if a.get("email", "").strip().lower() != clean_email
        ]
        # Also clean up legacy entries if present
        for eco in ["google", "m365"]:
            if eco in data and isinstance(data[eco], dict):
                if data[eco].get("email", "").strip().lower() == clean_email:
                    del data[eco]
                    original_len += 1
        deleted = len(data["accounts"]) < original_len
        if deleted:
            self._write_raw_vault(data)
        return deleted

    def log_consent(
        self,
        email: str,
        consent_text: str,
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """Automatically log explicit consent event into config/consent_log.json with IST timestamp."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        entries = []
        if CONSENT_LOG_FILE.exists():
            try:
                with open(CONSENT_LOG_FILE, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                entries = []

        try:
            ist_tz = pytz.timezone("Asia/Kolkata")
            now_ist = datetime.now(ist_tz).strftime("%Y-%m-%d %H:%M:%S IST")
        except Exception:
            now_ist = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S IST")

        entry = {
            "email": email.strip().lower(),
            "timestamp_ist": now_ist,
            "consent_text_accepted": consent_text,
            "status": status
        }
        entries.insert(0, entry)
        with open(CONSENT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=4)
        return entry

    def update_consent_status(self, email: str, status: str = "REVOKED_AND_WIPED") -> bool:
        """Update consent status in config/consent_log.json for DPDP Act instant revocation."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        entries = []
        if CONSENT_LOG_FILE.exists():
            try:
                with open(CONSENT_LOG_FILE, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                entries = []

        clean_email = email.strip().lower()
        try:
            ist_tz = pytz.timezone("Asia/Kolkata")
            now_ist = datetime.now(ist_tz).strftime("%Y-%m-%d %H:%M:%S IST")
        except Exception:
            now_ist = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S IST")

        for e in entries:
            if e.get("email", "").strip().lower() == clean_email:
                e["status"] = status
                e["revoked_at_ist"] = now_ist

        # Prepend explicit audit trail entry for revocation
        entries.insert(0, {
            "email": clean_email,
            "timestamp_ist": now_ist,
            "consent_text_accepted": f"Revocation / Kill-Switch triggered by user ({status})",
            "status": status
        })

        with open(CONSENT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=4)
        return True

    def get_consent_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent consent events from config/consent_log.json."""
        if not CONSENT_LOG_FILE.exists():
            return []
        try:
            with open(CONSENT_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)[:limit]
        except Exception:
            return []

    def has_active_consent(self, email: str) -> bool:
        """Check if an email has valid active consent (AUTHORIZED and not REVOKED_AND_WIPED)."""
        logs = self.get_consent_log(limit=500)
        clean_email = email.strip().lower()
        for e in logs:
            if e.get("email", "").strip().lower() == clean_email:
                return e.get("status") == "AUTHORIZED"
        return False

    def add_to_unsubscribed(self, email: str) -> bool:
        """Add email to config/unsubscribed.json so they are never contacted or scanned again."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        unsub_list = []
        if UNSUBSCRIBED_FILE.exists():
            try:
                with open(UNSUBSCRIBED_FILE, "r", encoding="utf-8") as f:
                    unsub_list = json.load(f)
            except Exception:
                unsub_list = []

        clean_email = email.strip().lower()
        if clean_email not in unsub_list:
            unsub_list.append(clean_email)
            with open(UNSUBSCRIBED_FILE, "w", encoding="utf-8") as f:
                json.dump(unsub_list, f, indent=4)
            return True
        return False

    def is_unsubscribed(self, email: str) -> bool:
        """Check if an email is in config/unsubscribed.json."""
        if not email or not UNSUBSCRIBED_FILE.exists():
            return False
        try:
            with open(UNSUBSCRIBED_FILE, "r", encoding="utf-8") as f:
                unsub_list = json.load(f)
                return email.strip().lower() in [u.strip().lower() for u in unsub_list]
        except Exception:
            return False

    def get_unsubscribed_list(self) -> List[str]:
        """Retrieve all unsubscribed/revoked email addresses."""
        if not UNSUBSCRIBED_FILE.exists():
            return []
        try:
            with open(UNSUBSCRIBED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def toggle_account(self, account_id: str, enabled: bool) -> bool:
        """Enable or disable an account."""
        data = self._read_raw_vault()
        for a in data.get("accounts", []):
            if a.get("id") == account_id:
                a["enabled"] = enabled
                self._write_raw_vault(data)
                return True
        return False

    def is_configured(self, ecosystem: Optional[str] = None) -> bool:
        """Check if at least one valid enabled account exists."""
        accounts = self.list_accounts(enabled_only=True)
        if ecosystem:
            accounts = [a for a in accounts if a.get("ecosystem") == ecosystem]
        for a in accounts:
            if a.get("ecosystem") == "google" and a.get("email") and a.get("app_password"):
                return True
            if a.get("ecosystem") == "m365" and a.get("email") and a.get("password"):
                return True
        return False

    def get_credentials(self) -> Dict[str, Any]:
        """Legacy helper for single-service access."""
        data = self._read_raw_vault()
        accounts = self.list_accounts(enabled_only=True)
        g_acc = next((a for a in accounts if a.get("ecosystem") == "google"), {})
        m_acc = next((a for a in accounts if a.get("ecosystem") == "m365"), {})
        return {
            "google": {
                "email": g_acc.get("email", ""),
                "app_password": g_acc.get("app_password", "")
            },
            "m365": {
                "email": m_acc.get("email", ""),
                "password": m_acc.get("password", ""),
                "tenant_id": m_acc.get("tenant_id", "")
            },
            "rdp": data.get("rdp", DEFAULT_VAULT["rdp"])
        }

    def save_credentials(self, credentials: Dict[str, Any]) -> None:
        """Legacy helper to save credentials."""
        for eco in ["google", "m365"]:
            if eco in credentials and credentials[eco].get("email"):
                acc_data = credentials[eco].copy()
                acc_data["ecosystem"] = eco
                acc_data["label"] = f"{eco.upper()} Account ({acc_data['email']})"
                acc_data["id"] = f"acc_{eco}_default"
                self.upsert_account(acc_data)
        if "rdp" in credentials:
            data = self._read_raw_vault()
            data["rdp"] = credentials["rdp"]
            self._write_raw_vault(data)
