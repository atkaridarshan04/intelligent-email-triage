"""
predictor.py — Main inference entry point.

Loads the active adapter from checkpoints/production/ and runs the full
parse → feature_extract → predict → route → postprocess pipeline.

Usage:
    predictor = Predictor()
    response = predictor.triage_eml(raw_eml_bytes)
    response = predictor.triage_json(parsed_dict)
    response = predictor.triage_record(email_record)
"""
import email as _email
import json
import re
import time
from email import policy
from pathlib import Path

from src.data.schema import AttachmentInfo, EmailRecord
from src.features.feature_pipeline import run as extract_features
from src.inference.adapter import LightGBMAdapter, ModelAdapter, STRUCTURED_COLS
from src.inference.postprocess import TriageResponse, build_response
from src.inference.threshold_router import route
from src.utils.io import email_id

_CHECKPOINT_DIR = Path(__file__).parents[2] / "checkpoints" / "production"


def _record_to_feature_dict(rec: EmailRecord) -> dict[str, float]:
    return {col: float(getattr(rec, col, 0.0)) for col in STRUCTURED_COLS}


def _record_to_text(rec: EmailRecord) -> str:
    return (rec.subject or "") + " [SEP] " + (rec.body_text or "")


class Predictor:
    def __init__(self, checkpoint_dir: Path = _CHECKPOINT_DIR):
        manifest = json.loads((checkpoint_dir / "manifest.json").read_text())
        model_type = manifest.get("model_type", "lightgbm")

        if model_type == "lightgbm":
            self._adapter: ModelAdapter = LightGBMAdapter(checkpoint_dir)
        else:
            raise ValueError(f"Unsupported model_type: {model_type}")

    def version(self) -> str:
        return self._adapter.version()

    def triage_record(self, rec: EmailRecord) -> TriageResponse:
        t0 = time.perf_counter()
        extract_features(rec)
        features = _record_to_feature_dict(rec)
        text = _record_to_text(rec)
        model_out = self._adapter.predict(text, features)
        routing = route(model_out.spam_prob, model_out.phishing_prob, features)
        latency_ms = (time.perf_counter() - t0) * 1000
        eid = rec.id or email_id(rec.subject, rec.body_text)
        return build_response(eid, model_out, routing, self._adapter.version(), latency_ms)

    def triage_eml(self, raw_bytes: bytes) -> TriageResponse:
        msg = _email.message_from_bytes(raw_bytes, policy=policy.default)

        subject = str(msg.get("Subject", ""))
        sender_address = str(msg.get("From", ""))
        reply_to = str(msg.get("Reply-To", ""))

        display_name = ""
        addr_match = re.match(r'^"?([^"<]+)"?\s*<([^>]+)>', sender_address)
        if addr_match:
            display_name = addr_match.group(1).strip()
            sender_address = addr_match.group(2).strip()

        body_text, body_html, urls, attachments = "", "", [], []
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if "attachment" in cd:
                attachments.append(AttachmentInfo(filename=part.get_filename("") or "", mime_type=ct))
            elif ct == "text/plain" and not body_text:
                body_text = part.get_content() or ""
            elif ct == "text/html" and not body_html:
                body_html = part.get_content() or ""

        urls = re.findall(r'https?://[^\s<>"\']+', body_text + body_html)
        rec = EmailRecord(
            subject=subject, body_text=body_text, body_html=body_html,
            sender_display_name=display_name, sender_address=sender_address,
            reply_to=reply_to, urls=urls, attachments=attachments,
        )
        rec.id = email_id(rec.subject, rec.body_text)
        return self.triage_record(rec)

    def triage_json(self, data: dict) -> TriageResponse:
        """Accept pre-parsed dict matching the API request schema."""
        attachments = [
            AttachmentInfo(filename=a.get("filename", ""), mime_type=a.get("mime_type", ""))
            for a in data.get("attachments", [])
        ]
        urls = data.get("urls", [])
        body_text = data.get("body_text", "")
        # Extract any URLs embedded in body_text that weren't explicitly passed
        if not urls and body_text:
            urls = re.findall(r'https?://[^\s<>"\']+', body_text)

        rec = EmailRecord(
            subject=data.get("subject", ""),
            body_text=body_text,
            sender_address=data.get("sender_address", data.get("from_addr", "")),
            reply_to=data.get("reply_to", ""),
            urls=urls,
            attachments=attachments,
        )
        rec.id = email_id(rec.subject, rec.body_text)
        return self.triage_record(rec)
