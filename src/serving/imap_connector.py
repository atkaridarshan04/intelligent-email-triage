"""
imap_connector.py — Live IMAP Mailbox Ingress Connector for Barclays Email Triage.

Connects to any live email account (Gmail, Outlook/Office 365, Yahoo, Fastmail, or corporate IMAP)
over TLS (Port 993) using an App Password. Fetches real incoming RFC-822 MIME emails,
saves them to the mailbox repository, and passes them directly to the ML triage pipeline.
"""

import email
import imaplib
import json
import logging
import os
import re
import ssl
import time
from email import policy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_MAILBOX_DATA_DIR = Path(__file__).parents[2] / "data" / "mailboxes"
_LIVE_CONFIG_PATH = _MAILBOX_DATA_DIR / "live_imap_config.json"

PROVIDER_PRESETS = {
    "gmail": {
        "name": "Google Gmail / Workspace",
        "server": "imap.gmail.com",
        "port": 993,
        "ssl": True,
        "help_url": "https://myaccount.google.com/apppasswords",
        "instructions": "Generate a 16-character App Password at: Google Account -> Security -> 2-Step Verification -> App Passwords.",
    },
    "outlook": {
        "name": "Microsoft Outlook / Office 365",
        "server": "outlook.office365.com",
        "port": 993,
        "ssl": True,
        "help_url": "https://account.live.com/proofs/manage/additional",
        "instructions": "Use an App Password generated under Microsoft Account -> Security -> Advanced Security Options.",
    },
    "yahoo": {
        "name": "Yahoo Mail",
        "server": "imap.mail.yahoo.com",
        "port": 993,
        "ssl": True,
        "help_url": "https://login.yahoo.com/account/security",
        "instructions": "Generate an App Password under Yahoo Account Security -> Generate App Password.",
    },
    "custom": {
        "name": "Custom Corporate IMAP",
        "server": "",
        "port": 993,
        "ssl": True,
        "help_url": "",
        "instructions": "Enter your corporate IMAP server hostname (e.g. mail.company.com).",
    },
}


def load_live_config() -> Optional[Dict[str, Any]]:
    """Loads stored live IMAP configuration if present."""
    if not _LIVE_CONFIG_PATH.exists():
        # Check environment variables as fallback
        env_user = os.environ.get("IMAP_USER", "")
        env_pass = os.environ.get("IMAP_PASSWORD", "")
        env_server = os.environ.get("IMAP_SERVER", "")
        if env_user and env_pass and env_server:
            return {
                "address": env_user,
                "server": env_server,
                "port": int(os.environ.get("IMAP_PORT", "993")),
                "password": env_pass,
                "folder": os.environ.get("IMAP_FOLDER", "INBOX"),
                "ssl": True,
                "enabled": True,
                "provider": "custom",
            }
        return None
    try:
        return json.loads(_LIVE_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Failed to read live IMAP config: {e}")
        return None


def save_live_config(config: Dict[str, Any]) -> None:
    """Saves live IMAP configuration to data/mailboxes/live_imap_config.json."""
    _MAILBOX_DATA_DIR.mkdir(parents=True, exist_ok=True)
    _LIVE_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def test_imap_connection(
    server: str,
    port: int,
    username: str,
    password: str,
    use_ssl: bool = True,
    timeout: int = 10,
) -> Tuple[bool, str]:
    """Tests connection and authentication to the remote IMAP server."""
    server = server.strip()
    username = username.strip()
    password = password.strip().replace(" ", "")  # Strip accidental spaces in app passwords

    if not server or not username or not password:
        return False, "Server, email address, and password/app password are required."

    try:
        if use_ssl:
            context = ssl.create_default_context()
            client = imaplib.IMAP4_SSL(server, port, ssl_context=context, timeout=timeout)
        else:
            client = imaplib.IMAP4(server, port, timeout=timeout)

        client.login(username, password)
        status, folders = client.list()
        client.logout()
        return True, "Successfully authenticated with IMAP mail server."
    except imaplib.IMAP4.error as e:
        err_msg = str(e)
        if "AUTHENTICATIONFAILED" in err_msg or "Invalid credentials" in err_msg:
            return False, "Authentication failed. Make sure you are using an App Password (not your standard account password)."
        return False, f"IMAP authentication error: {err_msg}"
    except Exception as e:
        return False, f"Connection failed to {server}:{port} — {e}"


def fetch_live_emails(
    server: str,
    port: int,
    username: str,
    password: str,
    folder: str = "INBOX",
    limit: int = 15,
    unread_only: bool = False,
    mark_as_read: bool = False,
    timeout: int = 15,
) -> List[Tuple[str, bytes]]:
    """
    Connects to the remote mailbox and retrieves recent RFC-822 email bytes.
    Returns list of tuples: [(message_uid, raw_bytes), ...]
    """
    server = server.strip()
    username = username.strip()
    password = password.strip().replace(" ", "")

    results: List[Tuple[str, bytes]] = []

    context = ssl.create_default_context()
    client = imaplib.IMAP4_SSL(server, port, ssl_context=context, timeout=timeout)

    try:
        client.login(username, password)
        status, _ = client.select(folder, readonly=not mark_as_read)
        if status != "OK":
            client.select("INBOX", readonly=not mark_as_read)

        search_criteria = "UNSEEN" if unread_only else "ALL"
        status, data = client.search(None, search_criteria)
        if status != "OK" or not data or not data[0]:
            client.logout()
            return []

        msg_ids = data[0].split()
        # Take the most recent messages up to limit
        selected_ids = msg_ids[-limit:]
        selected_ids.reverse()  # Newest first

        for mid in selected_ids:
            try:
                fetch_cmd = "(RFC822)" if mark_as_read else "(BODY.PEEK[])"
                status, msg_data = client.fetch(mid, fetch_cmd)
                if status != "OK" or not msg_data:
                    continue
                for response_part in msg_data:
                    if isinstance(response_part, tuple) and len(response_part) > 1:
                        raw_bytes = response_part[1]
                        msg_uid = mid.decode("utf-8", errors="ignore")
                        results.append((msg_uid, raw_bytes))
                        break
            except Exception as exc:
                logger.warning(f"Error fetching message {mid}: {exc}")

        client.logout()
    except Exception as exc:
        try:
            client.logout()
        except Exception:
            pass
        raise exc

    return results


def sync_live_mailbox(
    predictor=None,
    model_choice: str = "lightgbm",
    limit: int = 15,
) -> Dict[str, Any]:
    """
    Pulls real emails from the configured live IMAP mailbox, saves them into
    data/mailboxes/live-inbox/, executes triage inference, and logs to feedback.db.
    """
    config = load_live_config()
    if not config or not config.get("enabled"):
        return {
            "success": False,
            "synced_count": 0,
            "message": "No active live IMAP mailbox configured.",
        }

    address = config["address"]
    server = config["server"]
    port = config.get("port", 993)
    password = config["password"]
    folder = config.get("folder", "INBOX")

    dest_dir = _MAILBOX_DATA_DIR / "live-inbox"
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        raw_items = fetch_live_emails(
            server=server,
            port=port,
            username=address,
            password=password,
            folder=folder,
            limit=limit,
            unread_only=False,
            mark_as_read=False,
        )
    except Exception as e:
        return {
            "success": False,
            "synced_count": 0,
            "message": f"Failed to sync with {server}: {e}",
        }

    from src.feedback.store import FeedbackStore

    synced_count = 0
    for uid, raw_bytes in raw_items:
        try:
            msg = email.message_from_bytes(raw_bytes, policy=policy.default)
            subject = str(msg.get("Subject", "Untitled Email"))
            msg_id = str(msg.get("Message-ID", f"live-{uid}"))
            # Make a clean filename based on sanitized subject or UID
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", subject[:30]).strip("_") or f"msg_{uid}"
            filename = f"live_{uid}_{safe_name}.eml"
            file_path = dest_dir / filename

            # Only write and triage if we haven't already saved this file
            if not file_path.exists():
                file_path.write_bytes(raw_bytes)
                synced_count += 1

                # If predictor is provided, run immediate triage and save to database
                if predictor is not None:
                    try:
                        res = predictor.triage_eml(raw_bytes, model_choice=model_choice)
                        FeedbackStore().save_triage(
                            result=res,
                            subject=subject,
                            body_text=raw_bytes.decode("utf-8", errors="replace")[:1000],
                            features=res.features,
                        )
                    except Exception as triage_err:
                        logger.warning(f"Predictor error on live email {filename}: {triage_err}")

        except Exception as err:
            logger.warning(f"Error processing synced email {uid}: {err}")

    return {
        "success": True,
        "synced_count": synced_count,
        "total_fetched": len(raw_items),
        "mailbox": address,
        "message": f"Synced {synced_count} new email(s) from {address}.",
    }
