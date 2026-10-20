# 3-Minute Live Demo Walkthrough (Screen Narration)
## Sentinel Defense: Live Product Walkthrough

> **Duration:** Strictly 3 Minutes (180 Seconds)  
> **Spoken Word Count:** 465 words (~150 words/min — calibrated to comfortably fill 2:55 to 3:00)  
> **Style:** 100% live screen narration. Short sentences. Conversational, hands-on tone. No formal speechifying.  
> **PPT Context:** Embedded after problem slides; starts directly on the working software.  
> **Rules:** Zero assumed timing numbers, zero spoken shortcut keys.

---

## 📋 Presenter's Quick Setup

1. Tab 1: `http://127.0.0.1:8000/app/?tab=mailbox` (Live Triage Console)
2. Tab 2: `http://127.0.0.1:8000/app/queue?view=campaigns` (SOC Review Queue)
3. Tab 3: `http://127.0.0.1:8000/app/retrain` (Model Retraining Studio)
4. *Silent triggers (do NOT speak these):*  
   - Click `Send Phishing` (or silent tap <kbd>1</kbd>) = launches single phishing attack  
   - Click `Attack Campaign (+5)` (or silent tap <kbd>5</kbd>) = launches 5-message campaign

---

## ⏱️ Timeline Overview

```
┌──────────────┬────────────────────────┬────────────────────────────────────────────────────────┐
│ Timestamp    │ What Viewer Sees       │ What You Show & Say (Short & Punchy)                   │
├──────────────┼────────────────────────┼────────────────────────────────────────────────────────┤
│ 0:00 - 0:35  │ /app/?tab=mailbox      │ Live dashboard, TLS connection, 3 tiers, dual models   │
│ 0:35 - 1:15  │ /app/?tab=mailbox      │ Live phishing test, quarantine & reasons panel         │
│ 1:15 - 1:55  │ /app/?tab=mailbox      │ 5-email wire attack grouped into single cluster        │
│ 1:55 - 2:30  │ /app/queue             │ Unified campaign card & 1-click purge across inboxes   │
│ 2:30 - 3:00  │ /app/retrain           │ Retraining studio, quality gate, hot-reloading         │
└──────────────┴────────────────────────┴────────────────────────────────────────────────────────┘
```

---

# 🎙️ Verbatim Demo Narration & Actions

---

### [0:00 – 0:35] 1. Live Dashboard & Stream
* **On Screen:** Tab 1 (`/app/?tab=mailbox`).
* **Mouse Action:** Point to the top status badge `🟢 Live IMAP Active`, the three routing badges, and the model switcher buttons.
* **🎙️ Say This (85 words):**
  > "Here’s our live triage dashboard.
  >
  > Right at the top, you can see our live mailbox connected over TLS. Every incoming report lands right here in real time.
  >
  > The system routes every message into three distinct tiers: clear phishing is quarantined automatically, legitimate mail passes safely, and boundary cases are sent to our SOC analysts.
  >
  > We support two inference engines: a fast LightGBM model for sub-millisecond triage, and a RoBERTa transformer for deeper semantic understanding. You can switch between them anytime."

---

### [0:35 – 1:15] 2. Catching Phishing & Showing Reasons
* **On Screen:** Tab 1 (`/app/?tab=mailbox`).
* **Mouse Action:**
  1. Click `Send Phishing` (or silent key).
  2. Point to the HUD notification.
  3. Scroll to the dossier: point to red **`AUTO-QUARANTINE`** and red-flag reasons.
  4. Click the **RoBERTa** toggle to show model consensus.
* **🎙️ Say This (98 words):**
  > "Let’s bring in a live phishing attack.
  >
  > There it is in the inbox stream.
  >
  > It's evaluated instantly, classified as high-confidence phishing, and routed straight to auto-quarantine.
  >
  > Crucially, the model explains its reasoning. Down here in the inspection panel, we can see the exact red flags.
  >
  > It caught an authenticated sender mismatch, an obfuscated login link, and coercive language.
  >
  > If an analyst wants a second opinion, we can toggle RoBERTa right here. Both models agree with high confidence.
  >
  > Once quarantined, this threat signature is remembered in memory to block identical attacks immediately."

---

### [1:15 – 1:55] 3. Coordinated Attack Campaign
* **On Screen:** Tab 1 (`/app/?tab=mailbox`).
* **Mouse Action:**
  1. Click `Attack Campaign (+5)` (or silent key).
  2. Show 5 emails land in the table.
  3. Point to the purple **`CAMPAIGN CLUSTER`** tags on each row.
  4. Click the top email to highlight the purple warning banner with the cluster ID.
* **🎙️ Say This (96 words):**
  > "Now let's see how the system handles a coordinated attack campaign.
  >
  > Real-world attackers rarely send just one email. They target multiple employees across finance, legal, and executive teams.
  >
  > They subtly change employee names, invoice codes, and subject lines to bypass basic filters.
  >
  > Let's launch that attack now.
  >
  > Five variations land across our company mailboxes.
  >
  > Instead of flooding the feed with five separate alarms, the engine uses fuzzy clustering.
  >
  > It groups all five messages under this single purple campaign banner. It recognizes they are part of the exact same coordinated threat."

---

### [1:55 – 2:30] 4. SOC Review Queue & 1-Click Fix
* **On Screen:** Click the purple banner link (or switch to Tab 2: `/app/queue?view=campaigns`).
* **Mouse Action:**
  1. Point to the single consolidated Campaign Incident card showing all 5 targeted employees.
  2. Point to the metrics at the top (deduplication & volume reduction).
  3. Click the red button: **`Confirm Phishing & Quarantine All (5)`**.
  4. Show the card resolve and disappear.
* **🎙️ Say This (91 words):**
  > "Let’s jump over to the SOC Review Queue.
  >
  > Here is that entire five-target campaign on a single incident card.
  >
  > The analyst sees the root domain, the lure pattern, and every targeted employee in one unified view.
  >
  > Notice the metrics at the top: clustering reduces repetitive analyst review load by over eighty percent.
  >
  > Instead of reviewing five identical tickets one by one, we click 'Quarantine All' right here.
  >
  > Instantly, all five malicious emails are purged from every inbox across the company.
  >
  > One click protects the entire enterprise."

---

### [2:30 – 3:00] 5. Retraining Studio & Model Governance
* **On Screen:** Switch to Tab 3 (`/app/retrain`) — Model Retraining Studio.
* **Mouse Action:**
  1. Point to the feedback samples counter (the 5 reviewed emails now added as training samples).
  2. Hover over the training modes.
  3. Point to the automated Quality Gate checklist and hot-reload badge.
* **🎙️ Say This (95 words):**
  > "Finally, let’s look at the Model Retraining Studio.
  >
  > Every verdict our SOC analysts submit automatically feeds into this continuous learning dataset.
  >
  > When we trigger a retrain, the platform enforces an automated Quality Gate.
  >
  > A new candidate model must maintain our strict phishing recall standards on test data before it can ever be approved.
  >
  > Once verified, it deploys instantly with zero-downtime hot reloading. The live API swaps model weights in memory without restarting services or dropping requests.
  >
  > That completes the entire loop: instant detection, campaign triage, and automated model governance.
  >
  > Thank you."

---

## 🎯 Quick Demo Cheatsheet

| Segment | What to Click / Touch | What to Say |
|:---|:---|:---|
| **1. Stream (0:00–0:35)** | Hover on TLS badge, 3 tiers, & model toggles | "Here's our live triage dashboard... routes into three distinct tiers..." |
| **2. Phishing (0:35–1:15)** | Click `Send Phishing`, point to red flags, toggle RoBERTa | "Let's bring in a live phishing attack... explains its reasoning... remembered in memory..." |
| **3. Campaign (1:15–1:55)** | Click `Attack Campaign (+5)`, point to purple tags | "Now let's see how the system handles a coordinated attack campaign... fuzzy clustering..." |
| **4. Queue (1:55–2:30)** | Switch to `/app/queue`, click "Quarantine All (5)" | "Here is that entire five-target campaign on a single incident card... one click protects the enterprise..." |
| **5. Retrain (2:30–3:00)** | Switch to `/app/retrain`, point to quality gate & hot-reload | "Finally, let's look at the Retraining Studio... automated Quality Gate... zero-downtime hot reloading..." |
