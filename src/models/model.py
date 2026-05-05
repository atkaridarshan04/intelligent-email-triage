"""
Multimodal email triage model.

Architecture:
    Text:       RoBERTa (roberta-base) → 768-dim CLS embedding
    Metadata:   MLP over 10 structured features → 64-dim
    Behavioral: MLP over 2 behavioral features  → 16-dim
    Fusion:     concat(768 + 64 + 16) → Linear → 3-class softmax

Input feature order must match training:
    metadata  (10): spf_result, dkim_result, dmarc_result, url_count,
                    attachment_count, reply_to_mismatch, html_text_ratio,
                    tld_risk_score, url_count (dup removed), html_text_ratio
              actual 10: see METADATA_FEATURES below
    behavioral (2): sender_seen_before, first_time_domain
"""

import torch
import torch.nn as nn
from transformers import RobertaModel

CLASSES = ["spam", "junk", "phishing"]

METADATA_FEATURES = [
    "spf_result_enc",       # encoded: pass=0, softfail=1, fail=2, none=3
    "dkim_result_enc",
    "dmarc_result_enc",
    "url_count",
    "attachment_count",
    "reply_to_mismatch",    # 0/1
    "html_text_ratio",
    "tld_risk_score",
]

BEHAVIORAL_FEATURES = [
    "sender_seen_before",   # 0/1
    "first_time_domain",    # 0/1
]

AUTH_ENC = {"pass": 0, "softfail": 1, "neutral": 1, "fail": 2, "none": 3,
            "permerror": 2, "temperror": 2}


class MetadataMLP(nn.Module):
    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, out_dim), nn.ReLU(),
        )

    def forward(self, x):
        return self.net(x)


class EmailTriageModel(nn.Module):
    def __init__(self, roberta_name: str = "roberta-base", num_classes: int = 3):
        super().__init__()
        self.roberta     = RobertaModel.from_pretrained(roberta_name)
        self.meta_mlp    = MetadataMLP(in_dim=8,  out_dim=64)
        self.behav_mlp   = MetadataMLP(in_dim=2,  out_dim=16)
        self.classifier  = nn.Linear(768 + 64 + 16, num_classes)
        self.dropout     = nn.Dropout(0.1)

    def forward(
        self,
        input_ids:      torch.Tensor,   # (B, seq_len)
        attention_mask: torch.Tensor,   # (B, seq_len)
        metadata:       torch.Tensor,   # (B, 8)
        behavioral:     torch.Tensor,   # (B, 2)
    ) -> torch.Tensor:                  # (B, 3) logits
        cls = self.roberta(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0]
        cls = self.dropout(cls)
        meta_out  = self.meta_mlp(metadata)
        behav_out = self.behav_mlp(behavioral)
        fused     = torch.cat([cls, meta_out, behav_out], dim=-1)
        return self.classifier(fused)
