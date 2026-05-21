from dataclasses import dataclass, field


@dataclass
class AttachmentInfo:
    filename: str = ""
    mime_type: str = ""


@dataclass
class EmailRecord:
    # --- Identity ---
    id: str = ""                        # sha256(subject + body_text[:500])

    # --- Content (transformer input) ---
    subject: str = ""
    body_text: str = ""
    body_html: str = ""

    # --- Sender (raw, for feature extraction) ---
    sender_display_name: str = ""
    sender_address: str = ""
    reply_to: str = ""
    headers: dict = field(default_factory=dict)

    # --- URLs (raw list, for feature extraction) ---
    urls: list[str] = field(default_factory=list)

    # --- Attachments (raw, for feature extraction) ---
    attachments: list[AttachmentInfo] = field(default_factory=list)

    # --- Structured features (MLP input) ---
    # Sender
    display_from_mismatch: bool = False
    reply_to_mismatch: bool = False
    free_email_sender: bool = False
    # URLs
    url_count: int = 0
    domain_count: int = 0
    shortened_url_present: bool = False
    suspicious_tld_present: bool = False
    ip_literal_url: bool = False
    url_entropy: float = 0.0
    typosquatting_detected: bool = False
    # Attachments
    has_attachment: bool = False
    attachment_type: str = ""
    executable_detected: bool = False
    macro_detected: bool = False
    # Text stats
    subject_length: int = 0
    body_length: int = 0
    uppercase_ratio: float = 0.0
    digit_ratio: float = 0.0
    punctuation_density: float = 0.0
    link_density: float = 0.0
    # Brand
    brand_mention: bool = False
    sender_brand_mismatch: bool = False

    # --- Manifest fields ---
    label: str = ""                     # "spam" | "phishing"
    source: str = ""
    era_bucket: str = ""                # "legacy" | "mid" | "recent"
    subtype: str = ""
    augmented: bool = False
    split: str = ""                     # "train" | "val" | "test"

    # --- Quality tracking ---
    missing_feature_count: int = 0
