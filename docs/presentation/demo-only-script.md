# Live Product Demo Script (100% Demo Only — No Slides)
## Intelligent Enterprise Email Triage Platform
### Duration: ~4 to 4.5 Minutes | Pure On-Screen Web Application Demonstration

> **Note:** This script is strictly for the **Live Software Demonstration**. Do not show any slides during this video. The screen remains entirely on the web application (`http://127.0.0.1:8000/app/`).

---

## 🖥️ Screen & Setup Checklist Before Hitting Record

1. **Clean Start**: Open `http://127.0.0.1:8000/app/queue`. Verify pending queue is `0`.
2. **Browser Display**: Google Chrome or Microsoft Edge at **110% zoom** in Fullscreen mode (`F11`).
3. **Browser Tabs Prepared**:
   - **Tab 1**: Live Ingestion & Triage Engine: `http://127.0.0.1:8000/app/`
   - **Tab 2**: SOC Incident Review Queue: `http://127.0.0.1:8000/app/queue`
   - **Tab 3**: Enterprise Audit Database: `http://127.0.0.1:8000/app/database`
4. **Mouse Movement**: Keep mouse movements smooth and purposeful. Rest cursor near active elements when speaking.

---

## ⏱️ Video Timeline Summary

| Timestamp | Screen URL | Core Demonstration Feature |
| :--- | :--- | :--- |
| **0:00 – 0:35** | `/app/` | Platform Orientation & Live Ingestion Interface |
| **0:35 – 1:15** | `/app/` | Scenario 1: Benign Corporate Email Deflection (Zero False Positives) |
| **1:15 – 2:00** | `/app/` | Scenario 2: Phishing Detection, Platt Calibration & Explainability |
| **2:00 – 2:55** | `/app/queue` | Scenario 3: Attack Campaign Influx & SimHash Deduplication (10:1 Ratio) |
| **2:55 – 3:25** | `/app/queue` | Scenario 4: 1-Click Analyst Bulk Remediation & Hot-Cache Commit |
| **3:25 – 4:05** | `/app/` | Scenario 5: Hero Moment — Sub-2ms Fast-Path Closed-Loop Deflection |
| **4:05 – 4:40** | `/app/database` | Scenario 6: Regulatory Audit Trail, Campaign Badges & CSV Export |
| **4:40 – 4:55** | `/app/` | Wrap-Up & Closing Statement |

---

# Complete Word-for-Word Voiceover & Action Script

---

### [0:00 – 0:35] SEGMENT 1: PLATFORM ORIENTATION & INGESTION BENCH
* **URL on Screen**: `http://127.0.0.1:8000/app/`
* **Visual Action**:
  - Start directly on the live dashboard.
  - Hover the cursor briefly over the email input fields (Sender, Subject, Body).
  - Hover over the model selection dropdown showing **`LightGBM Champion (Default - 14ms)`** and **`RoBERTa Contextual Transformer`**.
* **🎙️ Voiceover (Read Verbatim)**:
  > "Welcome to the live demonstration of the **Intelligent Enterprise Email Triage Platform**.
  > 
  > What you see on screen is our live Tier-1 Cyber Defense analyst workbench. In production, this engine hooks directly into enterprise email feeds from Microsoft Defender and Proofpoint, processing thousands of user-reported emails in real time.
  > 
  > At the core of the engine is our **Dual-Engine pipeline**: a 14-millisecond LightGBM Champion model for blazing inference, backed by a deep RoBERTa contextual transformer for ambiguous lures. 
  > 
  > Let's walk through how this system transforms end-to-end SOC operations across real enterprise scenarios."

---

### [0:35 – 1:15] SEGMENT 2: BENIGN CORPORATE COMMS DEFLECTION
* **URL on Screen**: `http://127.0.0.1:8000/app/`
* **Visual Action**:
  1. Click the green sample button: **`[ 🟢 Benign Comms ]`**.
  2. Point the mouse to the populated fields:
     - Sender: `hr-benefits@company.com`
     - Subject: *"URGENT: Annual Benefits Open Enrollment Closes Friday"*
  3. Click the primary button: **`Execute Triage Pipeline`**.
* **Visual Result**:
  - A clean green card displays instantly with badge: **`VERIFIED BENIGN / LEGITIMATE`**.
  - Point to **Trust Score: `95.0%`**.
  - Point to **Latency: `11 ms`** and **Routing: `Automated Routing (No Action Required)`**.
* **🎙️ Voiceover (Read Verbatim)**:
  > "Our first scenario tackles the biggest driver of SOC analyst burnout: **benign corporate false alarms**.
  > 
  > Here, an employee reports an urgent HR announcement regarding benefits enrollment. Traditional spam filters frequently misclassify words like 'URGENT' and 'Immediate Action Required' as high-risk phishing.
  > 
  > Watch our platform: in just **11 milliseconds**, our Threat-Absent Origin Validation detects that the sender domain `@company.com` is authentic, verifies zero malicious payload markers, and routes the email as **`VERIFIED BENIGN`** with a 95% trust score.
  > 
  > This deflects benign false alarms automatically—saving analyst hours and preventing clean corporate emails from corrupting our machine learning training sets."

---

### [1:15 – 2:00] SEGMENT 3: PHISHING DETECTION & EXPLAINABILITY
* **URL on Screen**: `http://127.0.0.1:8000/app/`
* **Visual Action**:
  1. Click the red sample button: **`[ 🚨 Urgent Credential ]`** (or **`[ ⚠️ Standard Phishing ]`**).
  2. Point out the spoofed external sender domain: `security-update@company-security-portal.com`.
  3. Click **`Execute Triage Pipeline`**.
* **Visual Result**:
  - Card turns red with badge: **`CONFIRMED PHISHING`**.
  - Show **Phishing Probability: `98.8%`**.
  - Scroll down slightly to showcase the **Explainability & Risk Factor Breakdown** (Domain spoofing flag, URL lexical entropy, credential harvesting intent).
* **🎙️ Voiceover (Read Verbatim)**:
  > "Now, let's test a targeted credential harvesting attack. Notice the sender domain: `company-security-portal.com`—a classic typosquatting lookalike designed to trick employees.
  > 
  > Within **14 milliseconds**, our LightGBM model detects the threat, outputting a calibrated **98.8% phishing probability**. 
  > 
  > Because we use **Platt sigmoid calibration**, this isn't an arbitrary score—it represents true mathematical confidence. 
  > 
  > Looking below at our explainability dossier, the analyst can instantly inspect why: the system highlights the brand domain mismatch, the high-entropy suspicious URL, and the credential harvesting signature. Every decision is fully transparent and auditable."

---

### [2:00 – 2:55] SEGMENT 4: ATTACK CAMPAIGN INFLUX & SIMHASH DEDUPLICATION
* **URL on Screen**: Switch to **Tab 2 (`http://127.0.0.1:8000/app/queue`)**.
* **Visual Action**:
  1. Show that the review queue is currently clear at 0 pending.
  2. Click the red button: **`[ ⚡ Simulate Attack Campaign (+10 Reports) ]`**.
  3. The screen reloads instantly. Move the cursor smoothly to the top **SOC Operational ROI** metrics cards:
     - Hover over **Queue Compression Ratio: `10.0 : 1`**.
     - Hover over **Analyst Effort Saved: `90.0%`**.
  4. Scroll down to show the queue: there is only **ONE consolidated Campaign Incident Card** (`camp_1e677b7281`).
  5. Click the toggle link: **`View 10 impacted employee reports & dossiers ▾`** to reveal all 10 reports nested cleanly inside!
  6. Point out that each report has randomized invoice numbers and hit different mailboxes.
* **🎙️ Voiceover (Read Verbatim)**:
  > "Now let's examine what happens during a large-scale cyber attack. I'll switch to the **SOC Review Queue** and simulate a coordinated wire-fraud campaign hitting 10 different employees across the bank.
  > 
  > In a traditional SOC, this floods the queue with 10 separate tickets, forcing analysts to manually triage the exact same lure 10 times over.
  > 
  > In our platform, watch the top ROI metrics:
  > Our **64-bit SimHash Locality-Sensitive Hashing** normalizes randomized invoice numbers and subject variations. It clusters all 10 incoming alerts into **ONE consolidated Campaign Incident Card**, achieving a **10 to 1 queue compression ratio** and an immediate **90% reduction in analyst effort**.
  > 
  > Expanding the card, the analyst sees all 10 affected employees and individual dossiers unified in a single pane."

---

### [2:55 – 3:25] SEGMENT 5: 1-CLICK ANALYST BULK ACTION & HOT-CACHE COMMIT
* **URL on Screen**: Still on **Tab 2 (`http://127.0.0.1:8000/app/queue`)**.
* **Visual Action**:
  1. On that consolidated campaign card, click the green button: **`[ ⚡ Confirm Phishing (Bulk 10) ]`**.
  2. Point the mouse to the green banner that appears:
     *"Bulk action confirmed! 10 reports resolved and campaign signature committed to Fast-Path Hot-Cache."*
  3. Show the queue dropping back to 0 pending campaigns.
* **🎙️ Voiceover (Read Verbatim)**:
  > "The Tier-1 analyst inspects the unified dossier, verifies the malicious wire instruction, and with a single click executes **`Confirm Phishing (Bulk 10)`**.
  > 
  > Instantly, all 10 tickets are resolved in parallel, clearing the queue.
  > 
  > But here is the critical engineering breakthrough: behind the scenes, the platform extracts the SimHash fingerprint and commits it straight into our **Fast-Path Episodic Memory** hot cache."

---

### [3:25 – 4:05] SEGMENT 6: HERO MOMENT — SUB-2MS FAST-PATH DEFLECTION
* **URL on Screen**: Switch back to **Tab 1 (`http://127.0.0.1:8000/app/`)**.
* **Visual Action**:
  1. Click the purple sample button: **`[ ⚡ Fast-Path Lure ]`**.
  2. Point out that this is an 11th employee reporting another variation of the same campaign (*"URGENT: Outstanding Invoice Payment Overdue - Account #8812"*).
  3. Click **`Execute Triage Pipeline`**.
* **Visual Result**:
  - A prominent purple banner flashes at the top:
    **`⚡ Fast-Path Instant Verdict: Inherited from Human Analyst Decision`**
  - Point mouse to **Latency: `~1.2 ms`** (down from 14ms!).
  - Point mouse to **Decision Source: `Fast-Path Memory`** with **100% Trust Score**.
* **🎙️ Voiceover (Read Verbatim)**:
  > "Now, here is the hero moment of closed-loop intelligence.
  > 
  > Five minutes later, an 11th employee reports another copy of this lure. 
  > In conventional systems, this email would either trigger another ML inference or sit in the queue because scheduled retraining hasn't happened.
  > 
  > Look at what our system does:
  > In just **1.2 milliseconds**—without running heavy NLP or waiting overnight—the **Fast-Path Hot Cache** intercepts the signature, inherits the analyst's verdict, and deflects the threat with 100% confidence.
  > 
  > The human analyst taught the system once, and the entire enterprise is immunized instantly."

---

### [4:05 – 4:40] SEGMENT 7: ENTERPRISE AUDIT TRAIL & GOVERNANCE
* **URL on Screen**: Switch to **Tab 3 (`http://127.0.0.1:8000/app/database`)** (or click "Log & Database" in the nav bar).
* **Visual Action**:
  1. Point mouse to the table showing recent triages with their purple **`camp_1e677b7281`** badges.
  2. Hover over the top KPI cards: **Total Triaged**, **Agreement Rate (100%)**, and **Benign Comms Count**.
  3. Hover over the button: **`Export Audit Log (CSV)`**.
* **🎙️ Voiceover (Read Verbatim)**:
  > "Finally, enterprise security demands rigorous governance.
  > 
  > In our **SOC Database view**, every automated decision, campaign cluster ID, and analyst verdict is cryptographically hashed and logged to an immutable audit store. 
  > 
  > We maintain an exact audit trail of human-versus-machine agreement rates, and analysts can export the full dataset to CSV in one click for internal compliance and regulatory supervisory audits under PRA and FCA guidelines."

---

### [4:40 – 4:55] SEGMENT 8: CONCLUSION & WRAP-UP
* **URL on Screen**: Return smoothly to **Tab 1 (`http://127.0.0.1:8000/app/`)** with the clean interface visible.
* **Visual Action**: Park cursor neatly in the center.
* **🎙️ Voiceover (Read Verbatim)**:
  > "To summarize: by combining dual-engine machine learning with fuzzy SimHash deduplication and sub-2 millisecond episodic memory, we eliminate 90% of manual triage overhead while upholding an uncompromised 98% phishing recall standard.
  > 
  > Thank you for watching the live demonstration."

---

## 🎯 Rehearsal Tips for Maximum Impact

1. **Pacing**: Aim for ~130 words per minute. Don't rush; pauses while clicking buttons give the evaluators time to see the badges update.
2. **Audio Levels**: Speak with confidence into the microphone; emphasize key numbers (**"10 to 1 compression"**, **"90% effort saved"**, **"1.2 milliseconds"**, **"98% recall"**).
3. **Smooth Tabs**: Use `Ctrl+Tab` or clean mouse clicks to transition between the tabs without fumbling.
