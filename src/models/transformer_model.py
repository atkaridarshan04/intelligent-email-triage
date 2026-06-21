"""
transformer_model.py — Hybrid RoBERTa + MLP classifier.

Architecture used in Phase 3 (experimental, not in production).
Input: tokenised email text (RoBERTa) + structured feature vector (MLP).
Output: 2-class logits [spam, phishing].

Training is done on Kaggle (GPU T4 x2).
Saved artifact: roberta_hybrid_phase3.pt (model state dict) + phase3_temperature.pkl.

Inference adapter: TransformerAdapter satisfies the ModelAdapter protocol
and can be loaded by Predictor when manifest.json specifies model_type="transformer".
"""
import pickle
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset
from scipy.special import expit, logit
from scipy.optimize import minimize_scalar

from src.models.base import ModelAdapter, ModelOutput, STRUCTURED_COLS


# ---------------------------------------------------------------------------
# Training hyperparameters (Phase 3)
# ---------------------------------------------------------------------------

MAX_LEN    = 512
BATCH_SIZE = 16

TRAIN_PARAMS = {
    "epochs":        6,
    "lr":            1e-5,
    "warmup_ratio":  0.1,
    "label_smooth":  0.1,
    "weight_decay":  0.01,
    "patience":      3,
    "class_weights": [1.0, 1.5],  # upweight phishing
}


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class EmailDataset(Dataset):
    """Tokenises subject + body and bundles structured features."""

    def __init__(self, df, labels):
        from transformers import RobertaTokenizerFast
        self._tokenizer = RobertaTokenizerFast.from_pretrained("roberta-base")
        subj = df["subject"].fillna("").astype(str)
        body = df["body_text"].fillna("").astype(str)
        self.texts  = (subj + " </s> " + body).tolist()
        self.struct = torch.tensor(df[STRUCTURED_COLS].astype(float).values, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        enc = self._tokenizer(
            self.texts[idx],
            max_length=MAX_LEN,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "struct":         self.struct[idx],
            "label":          self.labels[idx],
        }


# ---------------------------------------------------------------------------
# Model architecture
# ---------------------------------------------------------------------------

class HybridEmailClassifier(nn.Module):
    """
    RoBERTa [CLS] embedding fused with a structured-feature MLP.

        RoBERTa-base  → 768-dim [CLS]
        MLP(19 → 64)  → 64-dim struct embedding
        Concat         → 832-dim
        Head(832→256→2)
    """

    def __init__(self, n_struct: int = len(STRUCTURED_COLS),
                 roberta_hidden: int = 768, mlp_hidden: int = 64, dropout: float = 0.3):
        super().__init__()
        from transformers import RobertaModel
        self.roberta = RobertaModel.from_pretrained("roberta-base")

        self.struct_encoder = nn.Sequential(
            nn.Linear(n_struct, mlp_hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(mlp_hidden, mlp_hidden), nn.ReLU(), nn.Dropout(dropout),
        )
        self.classifier = nn.Sequential(
            nn.Linear(roberta_hidden + mlp_hidden, 256), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(256, 2),
        )

    def forward(self, input_ids, attention_mask, struct):
        cls_emb    = self.roberta(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0, :]
        struct_emb = self.struct_encoder(struct)
        return self.classifier(torch.cat([cls_emb, struct_emb], dim=1))


# ---------------------------------------------------------------------------
# Loss
# ---------------------------------------------------------------------------

class LabelSmoothingLoss(nn.Module):
    """Label smoothing (ε=0.1) prevents overconfidence and improves ECE."""

    def __init__(self, smoothing: float = 0.1, weight=None):
        super().__init__()
        self.smoothing = smoothing
        self.weight    = weight

    def forward(self, logits, targets):
        n_classes = logits.size(1)
        with torch.no_grad():
            soft = torch.full_like(logits, self.smoothing / (n_classes - 1))
            soft.scatter_(1, targets.unsqueeze(1), 1.0 - self.smoothing)
        log_prob = nn.functional.log_softmax(logits, dim=1)
        loss = -(soft * log_prob).sum(dim=1)
        if self.weight is not None:
            loss = loss * self.weight[targets]
        return loss.mean()


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

def fit_temperature_scaling(raw_proba: np.ndarray, y: np.ndarray) -> float:
    def loss(T):
        p = np.clip(expit(logit(np.clip(raw_proba, 1e-7, 1 - 1e-7)) / T), 1e-7, 1 - 1e-7)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

    return float(minimize_scalar(loss, bounds=(0.1, 10.0), method="bounded").x)


# ---------------------------------------------------------------------------
# Inference adapter (artifact plugin)
# ---------------------------------------------------------------------------

class TransformerAdapter:
    """
    Loads roberta_hybrid_phase3.pt + phase3_temperature.pkl and satisfies
    the ModelAdapter protocol. Registered in Predictor for model_type="transformer".
    """

    def __init__(self, checkpoint_dir: Path):
        from transformers import RobertaTokenizerFast
        import json

        manifest  = json.loads((checkpoint_dir / "manifest.json").read_text())
        artifacts = manifest.get("artifacts", {})
        self._version   = manifest["version"]
        self._device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer = RobertaTokenizerFast.from_pretrained("roberta-base")

        self._model = HybridEmailClassifier(n_struct=len(STRUCTURED_COLS))
        state = torch.load(checkpoint_dir / artifacts.get("model", "roberta_hybrid_phase3.pt"),
                           map_location=self._device)
        self._model.load_state_dict(state)
        self._model.to(self._device).eval()

        with open(checkpoint_dir / artifacts.get("temperature", "phase3_temperature.pkl"), "rb") as f:
            self._T = pickle.load(f)["T"]

    def predict(self, text: str, features: dict[str, float]) -> ModelOutput:
        enc = self._tokenizer(text, max_length=MAX_LEN, padding="max_length",
                              truncation=True, return_tensors="pt")
        struct = torch.tensor(
            [[features.get(c, 0.0) for c in STRUCTURED_COLS]], dtype=torch.float32
        ).to(self._device)

        with torch.no_grad():
            logits = self._model(
                enc["input_ids"].to(self._device),
                enc["attention_mask"].to(self._device),
                struct,
            )
        raw = torch.softmax(logits, dim=1)[0, 1].item()
        p_phishing = float(expit(logit(np.clip(raw, 1e-7, 1 - 1e-7)) / self._T))

        # Transformer attributions not implemented — return empty dict
        return ModelOutput(spam_prob=1.0 - p_phishing, phishing_prob=p_phishing,
                           feature_attributions={})

    def version(self) -> str:
        return self._version

    def model_type(self) -> str:
        return "transformer"
