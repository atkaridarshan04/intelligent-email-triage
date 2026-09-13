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
from src.models.base import ModelAdapter, STRUCTURED_COLS
from src.models.lgbm_model import LightGBMAdapter
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
        self._checkpoint_dir = checkpoint_dir
        self._adapters: dict[str, ModelAdapter] = {}
        
        manifest = json.loads((checkpoint_dir / "manifest.json").read_text())
        model_type = manifest.get("model_type", "lightgbm")

        # Always initialize default adapter
        if model_type == "lightgbm":
            self._default_adapter: ModelAdapter = LightGBMAdapter(checkpoint_dir)
            self._adapters["lightgbm"] = self._default_adapter
        elif model_type == "transformer":
            from src.models.transformer_model import TransformerAdapter
            self._default_adapter = TransformerAdapter(checkpoint_dir)
            self._adapters["transformer"] = self._default_adapter
        else:
            raise ValueError(f"Unsupported model_type: {model_type}")

    def version(self, model_choice: str | None = None) -> str:
        return self.get_adapter(model_choice).version()

    def is_transformer_ready(self) -> bool:
        root = Path(__file__).parents[2]
        art_pt = root / "artifacts" / "transformer" / "model.pt"
        p3_pt = root / "checkpoints" / "phase3" / "roberta_hybrid_phase3.pt"
        return art_pt.exists() or p3_pt.exists()

    def get_adapter(self, model_choice: str | None = None) -> ModelAdapter:
        if not model_choice or model_choice in ("lightgbm", "default", "production"):
            if "lightgbm" not in self._adapters:
                self._adapters["lightgbm"] = LightGBMAdapter(self._checkpoint_dir)
            return self._adapters["lightgbm"]

        norm_choice = model_choice.lower().strip()
        if norm_choice in ("transformer", "roberta", "phase3", "deep_hybrid"):
            if "transformer" not in self._adapters:
                from src.models.transformer_model import TransformerAdapter
                self._adapters["transformer"] = TransformerAdapter()
            return self._adapters["transformer"]

        # Default fallback
        return self._default_adapter

    def available_models(self) -> list[dict]:
        return [
            {
                "id": "lightgbm",
                "name": "LightGBM",
                "type": "tabular_ensemble",
                "latency_target": "~14ms",
                "version": self.get_adapter("lightgbm").version(),
                "description": "Production baseline. Calibrated gradient boosted decision trees over 19 security features + TF-IDF.",
                "is_default": True,
                "is_available": True,
            },
            {
                "id": "transformer",
                "name": "RoBERTa",
                "type": "deep_neural",
                "latency_target": "~42ms",
                "version": "roberta-hybrid-v3.0",
                "description": "Contextual language representation fused with structured tabular MLP. Sub-0.05 Expected Calibration Error.",
                "is_default": False,
                "is_available": self.is_transformer_ready(),
            },
        ]

    def triage_record(
        self,
        rec: EmailRecord,
        explicit_features: dict | None = None,
        model_choice: str | None = None,
    ) -> TriageResponse:
        adapter = self.get_adapter(model_choice)
        t0 = time.perf_counter()
        extract_features(rec)
        if explicit_features:
            for k, v in explicit_features.items():
                if hasattr(rec, k):
                    setattr(rec, k, v)
        features = _record_to_feature_dict(rec)
        text = _record_to_text(rec)
        model_out = adapter.predict(text, features)
        routing = route(model_out.spam_prob, model_out.phishing_prob, features)
        latency_ms = (time.perf_counter() - t0) * 1000
        eid = rec.id or email_id(rec.subject, rec.body_text)
        return build_response(
            eid,
            model_out,
            routing,
            adapter.version(),
            latency_ms,
            feature_values=features,
        )

    def triage_eml(self, raw_bytes: bytes, model_choice: str | None = None) -> TriageResponse:
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
            fn = part.get_filename("") or ""
            if "attachment" in cd or (fn and ct not in ("text/plain", "text/html")):
                attachments.append(AttachmentInfo(filename=fn, mime_type=ct))
            elif ct == "text/plain" and not body_text and "attachment" not in cd:
                try:
                    body_text = part.get_content() or ""
                except Exception:
                    payload = part.get_payload(decode=True)
                    body_text = payload.decode("utf-8", errors="replace") if payload else ""
            elif ct == "text/html" and not body_html and "attachment" not in cd:
                try:
                    body_html = part.get_content() or ""
                except Exception:
                    payload = part.get_payload(decode=True)
                    body_html = payload.decode("utf-8", errors="replace") if payload else ""

        if not body_text and not body_html:
            try:
                body_content = msg.get_body(preferencelist=('plain', 'html'))
                body_text = body_content.get_content() if body_content else str(msg.get_payload() or "")
            except Exception:
                body_text = str(msg.get_payload() or "")

        if not body_text and body_html:
            body_text = re.sub(r'<[^>]+>', ' ', body_html).strip() or body_html

        urls = re.findall(r'https?://[^\s<>"\']+', (body_text or "") + " " + (body_html or ""))
        rec = EmailRecord(
            subject=subject, body_text=body_text, body_html=body_html,
            sender_display_name=display_name, sender_address=sender_address,
            reply_to=reply_to, urls=urls, attachments=attachments,
        )
        rec.id = email_id(rec.subject, rec.body_text)
        return self.triage_record(rec, model_choice=model_choice)

    def triage_json(self, data: dict, model_choice: str | None = None) -> TriageResponse:
        """Accept pre-parsed dict matching the API request schema."""
        chosen_model = data.get("model") or model_choice
        attachments = [
            AttachmentInfo(filename=a.get("filename", ""), mime_type=a.get("mime_type", ""))
            for a in data.get("attachments", [])
        ]
        urls = data.get("urls", [])
        body_text = data.get("body_text", "")
        # Extract any URLs embedded in body_text that weren't explicitly passed
        if not urls and body_text:
            urls = re.findall(r'https?://[^\s<>"\']+', body_text)

        sender_address = data.get("sender_address", data.get("from_addr", ""))
        display_name = data.get("sender_display_name", "")
        if not display_name and "<" in sender_address:
            addr_match = re.match(r'^"?([^"<]+)"?\s*<([^>]+)>', sender_address)
            if addr_match:
                display_name = addr_match.group(1).strip()
                sender_address = addr_match.group(2).strip()

        rec = EmailRecord(
            subject=data.get("subject", ""),
            body_text=body_text,
            sender_display_name=display_name,
            sender_address=sender_address,
            reply_to=data.get("reply_to", ""),
            urls=urls,
            attachments=attachments,
        )
        rec.id = email_id(rec.subject, rec.body_text)
        explicit_features = {
            k: float(v) if isinstance(v, (int, float, bool)) else v
            for k, v in data.items()
            if hasattr(rec, k) and k not in ("id", "subject", "body_text", "body_html", "sender_display_name", "sender_address", "reply_to", "headers", "urls", "attachments", "model")
        }
        return self.triage_record(rec, explicit_features=explicit_features, model_choice=chosen_model)
