"""
Multimodal email triage model — matches training architecture in spam-phishing.ipynb.

Architecture:
    Text:     RoBERTa (roberta-base) → mean-pooled 768-dim embedding
    Metadata: Linear(10→64) → ReLU → LayerNorm → Dropout → 64-dim
    Fusion:   concat(768 + 64) → Linear → 3-class logits

Metadata vector (10 features, in order):
    spf_result      : pass=1.0, softfail=0.5, fail=0.0, none=-1.0
    dkim_result     : pass=1.0, fail=0.0, none=-1.0
    dmarc_result    : pass=1.0, fail=0.0, none=-1.0
    url_count       : float
    attachment_count: float
    reply_to_mismatch: 0.0 / 1.0
    html_text_ratio : float
    tld_risk_score  : float
    sender_seen_before: 0.0 / 1.0
    first_time_domain : 0.0 / 1.0
"""

import torch
import torch.nn as nn
from transformers import RobertaModel

CLASSES = ["spam", "junk", "phishing"]
LABEL2ID = {"spam": 0, "junk": 1, "phishing": 2}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}

SPF_MAP  = {"pass": 1.0, "softfail": 0.5, "fail": 0.0, "none": -1.0}
AUTH_MAP = {"pass": 1.0, "fail": 0.0, "none": -1.0}


class EmailTriageModel(nn.Module):
    def __init__(self, roberta_name: str = "roberta-base", num_classes: int = 3):
        super().__init__()
        self.encoder = RobertaModel.from_pretrained(roberta_name)
        self.meta = nn.Sequential(
            nn.Linear(10, 64),
            nn.ReLU(),
            nn.LayerNorm(64),
            nn.Dropout(0.3),
        )
        self.fc = nn.Linear(768 + 64, num_classes)

    def _pool(self, hidden: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Attention-mask-weighted mean pooling."""
        m = mask.unsqueeze(-1).float()
        return (hidden * m).sum(1) / m.sum(1)

    def forward(
        self,
        input_ids:      torch.Tensor,   # (B, seq_len)
        attention_mask: torch.Tensor,   # (B, seq_len)
        metadata:       torch.Tensor,   # (B, 10)
    ) -> torch.Tensor:                  # (B, 3) logits
        h = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        h = self._pool(h, attention_mask)
        m = self.meta(metadata)
        return self.fc(torch.cat([h, m], dim=-1))
