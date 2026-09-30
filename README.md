# ⚡ SmartCal Systems: Autonomous Email & Calendar Agent

Autonomous AI automation engine operating 24/7 across **Google Workspace (Gmail, Google Calendar)** and **Microsoft 365 (Outlook, Microsoft Teams)**.

---

## 🌟 Key Features

1. **Multi-Account & Multi-Tenant Support**:
   - Connect **unlimited** Google Workspace inboxes (e.g. `sales@`, `support@`, `ceo@`) and Microsoft 365 inboxes (e.g. `executive@enterprise.com`, `recruiting@`).
   - Individual account settings: Custom sender display names for signatures, account-specific auto-send toggles, and dedicated Drafts folder placement.
   - Target all accounts simultaneously or run scoped execution on a specific account (`--account <id>`).
2. **Dual Ecosystem Integration (Hybrid)**:
   - **Google Workspace**: Gmail IMAP/SMTP, Google Calendar event creation, Google Meet video links.
   - **Microsoft 365**: Outlook IMAP/SMTP, Microsoft Teams meeting generation, Outlook Calendar integration.
3. **Flexible Authentication & Access**:
   - **Direct Credentials Vault**: AES-GCM encrypted vault (`config/credentials.json`) storing credentials for all accounts safely.
   - **Remote Desktop (RDP) & Browser Automation**: Fallback to isolated local or remote browser instances when API access is restricted.
4. **Intelligent NLP Parsing Engine**:
   - Scans incoming unread emails across all accounts.
   - Extracts sender details, subject, agenda items, bulleted action items, dates, times, durations, and attendee lists.
5. **Contextual Draft Generation & Review Safety**:
   - Automatically constructs executive-grade replies with agenda points and calendar links under the proper account sender identity.
   - Leaves replies in the **Drafts** folder for user review (or can be configured to auto-send).
6. **Conflict Resolution & Calendar Scheduling**:
   - Checks calendar conflicts against existing appointments on each account's calendar.
   - Suggests alternative slots if a requested time is already occupied.
7. **Unified Web Management Dashboard & CLI**:
   - Modern dark-mode Streamlit dashboard with multi-account switcher, account cards, pause/resume controls, and credential management.
   - Rich terminal CLI with multi-account diagnostics, single-shot scans, and continuous background daemon modes.

---

## 🚀 Quick Start Guide

### 1. Verification & Diagnostics Across All Accounts
Run a diagnostics check to inspect all connected accounts:
```bash
python main.py --check
```

### 2. Immediate Multi-Account Scan
Trigger an immediate scanning and processing cycle across all accounts:
```bash
python main.py --scan
```
Or scan a single specific account:
```bash
python main.py --scan --account <account_id>
```

### 3. Interactive Web Dashboard
Launch the multi-account visual control center:
```bash
streamlit run ui/dashboard.py
```
*Navigate to the **👥 Manage Accounts (Multi-Tenant)** tab to add, pause, or configure accounts.*

### 4. Background Daemon (Continuous Monitoring)
Run the agent in continuous monitoring mode across all accounts (polling every 60 seconds):
```bash
python main.py --daemon --interval 60
```

### 5. Enterprise Simulation / Demo Mode
Test the end-to-end pipeline with realistic simulated enterprise emails and calendar invites:
```bash
python main.py --demo
```

---

## 🔐 Configuration & Credentials

Credentials and settings can be managed via the Web Dashboard or saved in:
- `config/settings.json`: Polling interval, trigger rules (`all_unread` vs `keywords`), and auto-send preferences.
- `config/credentials.json`: Encrypted credentials vault for Gmail, M365, and RDP.
