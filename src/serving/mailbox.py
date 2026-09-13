"""
mailbox.py — Live Mailbox Ingress Manager for Barclays Email Triage.

Zero fake mailboxes or preloaded clutter.
Focuses strictly on real-time stream ingestion:
  - Monitors the active live-connected mailbox (Gmail, Outlook, Yahoo, Corporate IMAP).
  - Indexes and parses real RFC-822 .eml files fetched from the remote mail server.
  - Feeds real emails directly to the LightGBM / RoBERTa inference engine for one-click triage.
"""

import email
import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass
from email import policy
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Base storage directory for connected mailboxes
_MAILBOX_DATA_DIR = Path(__file__).parents[2] / "data" / "mailboxes"


@dataclass
class MailboxDefinition:
    id: str
    address: str
    name: str
    department: str
    protocol: str
    status: str
    badge_text: str
    description: str
    is_custom: bool = True
    unread_count: int = 0


def _normalize_mailbox_id(id_or_addr: str) -> str:
    """Resolves mailbox identifier to local folder key ('live-inbox')."""
    return "live-inbox"


def get_available_mailboxes() -> List[Dict[str, Any]]:
    """
    Returns list of active mailboxes.
    Only returns a mailbox if a real Live IMAP account is connected.
    """
    try:
        from src.serving.imap_connector import load_live_config
        live_cfg = load_live_config()
        if live_cfg and live_cfg.get("enabled"):
            mb_dir = _MAILBOX_DATA_DIR / "live-inbox"
            eml_count = len(list(mb_dir.glob("*.eml"))) if mb_dir.exists() else 0

            provider_label = live_cfg.get("provider", "IMAP").upper()
            mb = MailboxDefinition(
                id="live-inbox",
                address=live_cfg["address"],
                name=f"Live Connected Mailbox ({live_cfg['address']})",
                department=f"Real-Time Stream ({provider_label})",
                protocol=f"IMAP4/TLS ({live_cfg.get('server', 'remote')}:993)",
                status="active",
                badge_text="🟢 Live IMAP Active",
                description=f"Real-time synchronized mailbox for {live_cfg['address']} via TLS 1.3.",
                is_custom=True,
            )
            d = asdict(mb)
            d["message_count"] = eml_count
            return [d]
    except Exception as exc:
        logger.warning(f"Error checking live mailbox config: {exc}")

    return []


def get_mailbox_feed(
    mailbox_id_or_addr: str = "live-inbox",
    predictor=None,
    model_choice: str = "lightgbm",
) -> List[Dict[str, Any]]:
    """
    Parses and triages real .eml messages from data/mailboxes/live-inbox/.
    Returns a sorted list (newest first) of real email records ready for UI display.
    """
    mb_dir = _MAILBOX_DATA_DIR / "live-inbox"
    if not mb_dir.exists():
        return []

    eml_files = sorted(mb_dir.glob("*.eml"), key=lambda p: p.stat().st_mtime, reverse=True)
    feed_items = []

    for path in eml_files:
        try:
            raw_bytes = path.read_bytes()
            msg = email.message_from_bytes(raw_bytes, policy=policy.default)
            subject = str(msg.get("Subject", "Untitled Message"))
            sender = str(msg.get("From", "Unknown Sender"))
            recipient = str(msg.get("To", ""))
            date_header = str(msg.get("Date", ""))
            message_id = str(msg.get("Message-ID", path.stem))

            # Extract body snippet
            body_text = ""
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body_text = part.get_content() or ""
                        if body_text:
                            break
                    except Exception:
                        pass
            if not body_text:
                body_text = raw_bytes.decode("utf-8", errors="replace")

            snippet = " ".join(body_text.strip().split()[:22])
            if len(snippet) > 140:
                snippet = snippet[:140] + "..."

            urls = re.findall(r'https?://[^\s<>"\\\']+', body_text)

            # Triage with real model
            label = "analyst_review"
            confidence = 0.50
            trust_score = 50.0
            security_override = False
            priority = "MEDIUM"

            if predictor is not None:
                try:
                    res = predictor.triage_eml(raw_bytes, model_choice=model_choice)
                    label = res.label
                    phish_p = res.calibrated_phishing_probability or res.phishing_probability
                    spam_p = res.calibrated_spam_probability or res.spam_probability
                    confidence = phish_p if label == "phishing" else spam_p
                    trust_score = getattr(res, "trust_score", 50.0)
                    security_override = getattr(res, "security_override", False)
                    if label == "phishing":
                        priority = "CRITICAL" if confidence >= 0.90 else "HIGH"
                    elif "review" in label:
                        priority = "HIGH"
                    else:
                        priority = "LOW"
                except Exception as e:
                    logger.debug(f"Predictor error on live email {path.name}: {e}")

            feed_items.append({
                "id": path.stem,
                "filename": path.name,
                "mailbox_id": "live-inbox",
                "subject": subject,
                "sender": sender,
                "recipient": recipient,
                "date": date_header or "Just now",
                "mtime": path.stat().st_mtime,
                "size_kb": round(path.stat().st_size / 1024, 1),
                "snippet": snippet,
                "url_count": len(urls),
                "label": label,
                "confidence": confidence,
                "trust_score": trust_score,
                "security_override": security_override,
                "priority": priority,
            })
        except Exception as exc:
            logger.warning(f"Error parsing live email {path.name}: {exc}")

    return feed_items


def get_eml_file_path(mailbox_id_or_addr: str, eml_id: str) -> Optional[Path]:
    """Returns absolute path to the .eml file in data/mailboxes/live-inbox/."""
    mb_dir = _MAILBOX_DATA_DIR / "live-inbox"
    if mb_dir.exists():
        for candidate in [f"{eml_id}.eml", eml_id]:
            p = mb_dir / candidate
            if p.exists():
                return p
    # Search all subdirectories as fallback
    for p in _MAILBOX_DATA_DIR.glob(f"**/{eml_id}*"):
        if p.is_file() and p.suffix == ".eml":
            return p
    return None


def disconnect_live_mailbox(clear_emails: bool = False) -> bool:
    """Disconnects the active live IMAP mailbox and optionally deletes fetched emails."""
    cfg_path = _MAILBOX_DATA_DIR / "live_imap_config.json"
    if cfg_path.exists():
        try:
            cfg_path.unlink()
        except Exception:
            pass

    if clear_emails:
        mb_dir = _MAILBOX_DATA_DIR / "live-inbox"
        if mb_dir.exists():
            for f in mb_dir.glob("*.eml"):
                try:
                    f.unlink()
                except Exception:
                    pass

    return True
