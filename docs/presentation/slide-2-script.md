# Slide 2: WHAT / Engineering Architecture
## 1-Minute Spoken Presentation Script

> **Target Duration:** Strictly 1:00 (60 Seconds)  
> **Spoken Word Count:** 126 words (~125 words/minute — natural, relaxed conversational pace)  
> **Speaker:** Student Team (You)  
> **Context:** Delivered during Slide 2 before switching directly to the 3-minute live screen demo.  
> **Rules:** Zero mention of Barclays, zero mention of 80k+ employees, zero assumed timing numbers.

---

## ⏱️ Timeline & On-Slide Pointers

```
┌──────────────┬──────────────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Timestamp    │ Where to Point on Slide 2                │ Spoken Narration Block                                 │
├──────────────┼──────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 0:00 - 0:15  │ Left: Inbound Ingest & 19 Features       │ Ingestion stream & 19 multimodal security signals      │
│ 0:15 - 0:30  │ Top-Center: SimHash & Dual Models        │ Fuzzy campaign clustering & LightGBM / RoBERTa engine  │
│ 0:30 - 0:45  │ Bottom-Center: Calibration & 3 Tiers     │ Calibrated 3-tier routing & explainable red flags      │
│ 0:45 - 1:00  │ Right: Fast-Path Memory & Retraining     │ Sub-2ms episodic memory & hand-off to live demo        │
└──────────────┴──────────────────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 🎙️ Verbatim Delivery Script

### [0:00 – 0:15] 1. Ingestion & Feature Extraction (28 words)
*👉 **Pointer:** Point to the left side of the diagram (Inbound Mailbox & Feature Extraction).*

> "Here is our end-to-end architecture.
>
> When an employee reports an email, we ingest it in real time and extract nineteen multimodal security signals alongside deep lexical features."

---

### [0:15 – 0:30] 2. Clustering & Dual-Engine Inference (38 words)
*👉 **Pointer:** Point to the center-top (64-bit SimHash Clustering & Dual Models).*

> "To prevent alert fatigue, our 64-bit SimHash engine fuzzy-clusters mutated attack variations into a single campaign card.
>
> For classification, LightGBM delivers sub-millisecond throughput, while a fine-tuned RoBERTa transformer validates complex, evasive language."

---

### [0:30 – 0:45] 3. Calibrated 3-Tier Routing (23 words)
*👉 **Pointer:** Point to the center-bottom (Platt Calibration & 3-Tier Confidence Router).*

> "Our calibrated confidence router automatically quarantines clear phishing, safely passes internal broadcasts, and sends boundary cases to analysts with transparent red-flag reasoning."

---

### [0:45 – 1:00] 4. Fast-Path Memory & Transition to Live Demo (37 words)
*👉 **Pointer:** Point to the right side (Fast-Path Hot-Cache & Retraining Loop).*

> "Once an analyst resolves a threat, Fast-Path memory immunizes the organization in under two milliseconds, while our retraining studio continuously evolves the model without downtime.
>
> Let’s jump straight into the live system to see this in action."

---

## 📄 Continuous Script (For Rehearsal / Teleprompter)

> "Here is our end-to-end architecture. When an employee reports an email, we ingest it in real time and extract nineteen multimodal security signals alongside deep lexical features.
>
> To prevent alert fatigue, our 64-bit SimHash engine fuzzy-clusters mutated attack variations into a single campaign card. For classification, LightGBM delivers sub-millisecond throughput, while a fine-tuned RoBERTa transformer validates complex, evasive language.
>
> Our calibrated confidence router automatically quarantines clear phishing, safely passes internal broadcasts, and sends boundary cases to analysts with transparent red-flag reasoning.
>
> Once an analyst resolves a threat, Fast-Path memory immunizes the organization in under two milliseconds, while our retraining studio continuously evolves the model without downtime. Let’s jump straight into the live system to see this in action."

---

## 🎯 Transition to Live Demo
The final phrase:  
`"Let’s jump straight into the live system to see this in action."`  
is your exact cue to switch windows to `http://127.0.0.1:8000/app/` and begin the **3-Minute Live Screen Walkthrough**.
