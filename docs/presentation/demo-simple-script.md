# Simple 4-Minute Live Demo Script (100% Demo Only — No Slides)
## Intelligent Enterprise Email Triage Platform

> **Format:** 100% Live Screen Recording on `http://127.0.0.1:8000/app/`.  
> **Duration:** ~3.5 to 4 Minutes.  
> **Style:** Simple, clear, plain English, conversational. No heavy jargon.

---

## 🛠️ Quick Setup (Do this before recording)
1. Open Chrome/Edge to `http://127.0.0.1:8000/app/` (Fullscreen, 110% zoom).
2. Have `http://127.0.0.1:8000/app/queue` open in a second tab (make sure it has 0 pending items).
3. Optional third tab: `http://127.0.0.1:8000/app/database`.

---

# ⏱️ Step-by-Step Script: What to Do & What to Say

---

### [0:00 – 0:25] 1. INTRODUCTION & THE CORE PROBLEM
* **Screen:** On `http://127.0.0.1:8000/app/`
* **What to Show:** Move mouse over the live dashboard and the sample buttons at the top (`Phishing`, `Spam`, `Benign Comms`).
* **🎙️ What to Say:**
  > "Hi everyone, welcome to the live demo of our Intelligent Email Triage Platform.
  > 
  > In an enterprise organization, employees report hundreds of suspicious emails every day. 
  > The core problem for security analysts is simple: **Is this email harmless nuisance spam, or is it dangerous phishing trying to steal credentials or money?**
  > 
  > Let's see how our platform solves this in real time."

---

### [0:25 – 0:55] 2. THE SPAM TEST (Harmless Junk)
* **Screen:** Still on `/app/`
* **What to Do:**
  1. Click the sample button: **`Spam`**.
  2. Click the primary button: **`Run Triage`**.
* **What to Show:** Point to the grey badge: **`CLASSIFIED AS SPAM`**, low threat score, and fast latency (~12ms).
* **🎙️ What to Say:**
  > "First, let's test a typical spam email. I'll click **`Spam`** and hit **`Run Triage`**.
  > 
  > In just **12 milliseconds**, the system classifies this as harmless spam. 
  > There are no malicious links, no spoofed domains, and no credential theft. 
  > 
  > Because the threat level is low, it is automatically routed away, so our Tier-1 analysts don't waste time on junk mail."

---

### [0:55 – 1:35] 3. THE PHISHING TEST (Dangerous Attack)
* **Screen:** Still on `/app/`
* **What to Do:**
  1. Click the sample button: **`Phishing`**.
  2. Click **`Run Triage`**.
* **What to Show:**
  - Red badge: **`PHISHING DETECTED`**.
  - High phishing probability (98%+).
  - Scroll down slightly to point to the reasons (brand domain mismatch, suspicious URL).
* **🎙️ What to Say:**
  > "Now let's test a real threat. I'll click **`Phishing`** and run triage.
  > 
  > Immediately, the card flashes red: **`PHISHING DETECTED`** with a 98% probability.
  > 
  > If we look at the explanation below, the system shows exactly why: it caught a fake lookalike domain impersonating the bank, high urgency words, and a link pointing to a known credential-harvesting server. 
  > 
  > It immediately flags this high-priority threat for action."

---

### [1:35 – 2:30] 4. THE ATTACK CAMPAIGN (10 Reports → 1 Card)
* **Screen:** Switch to the second tab: `http://127.0.0.1:8000/app/queue`
* **What to Do:**
  1. Click the red button: **`[ ⚡ Simulate Attack Campaign (+10 Reports) ]`**.
  2. Point mouse to the top metric: **Queue Compression Ratio: 10.0 : 1** and **Analyst Effort Saved: 90.0%**.
  3. Scroll to the single campaign card: `camp_1e677b7281` (*"URGENT: Outstanding Invoice Payment Overdue"*).
  4. Click **`View 10 impacted employee reports & dossiers ▾`** to expand it.
* **🎙️ What to Say:**
  > "Now, what happens during an actual cyber attack? 
  > Attackers don't just email one person; they blast 10 or 20 employees at the same time.
  > 
  > In a normal SOC, this creates 10 separate tickets, and an analyst has to review the exact same email 10 times.
  > 
  > Watch our platform: I'll simulate a 10-employee attack campaign.
  > 
  > Instead of 10 tickets, our fuzzy clustering groups all 10 reports into **ONE single Campaign Card**. 
  > That gives us a **10 to 1 compression ratio** and saves **90% of analyst effort**.
  > 
  > Expanding the card, you can see all 10 employee reports neatly grouped together, even though the attacker randomized the invoice numbers to try to evade detection."

---

### [2:30 – 3:00] 5. 1-CLICK BULK RESOLUTION
* **Screen:** Still on `/app/queue`
* **What to Do:**
  1. Click the green button on the campaign card: **`[ ⚡ Confirm Phishing (Bulk 10) ]`**.
  2. Point to the green confirmation message. Notice the queue drops back to 0 pending.
* **🎙️ What to Say:**
  > "The analyst reviews the campaign once, sees it's a wire-fraud scam, and clicks **`Confirm Phishing (Bulk 10)`**.
  > 
  > With just one click, all 10 tickets are resolved at once.
  > 
  > And behind the scenes, the system immediately commits this campaign signature into our **Fast-Path memory**."

---

### [3:00 – 3:35] 6. THE HERO MOMENT (Sub-2ms Fast-Path Memory)
* **Screen:** Switch back to the first tab: `http://127.0.0.1:8000/app/`
* **What to Do:**
  1. Click the purple sample button: **`[ ⚡ Fast-Path Lure ]`**.
  2. Point out that this is an 11th employee reporting the same invoice scam.
  3. Click **`Run Triage`**.
* **What to Show:**
  - Bright purple banner: **`⚡ Fast-Path Instant Verdict: Inherited from Human Analyst Decision`**.
  - Latency: **`~1.2 ms`**!
  - 100% Trust score.
* **🎙️ What to Say:**
  > "Now comes the best part: instant closed-loop defense.
  > 
  > Two minutes later, an 11th employee reports another copy of this email. 
  > In traditional systems, you have to wait overnight for models to retrain.
  > 
  > But look at our system:
  > In just **1.2 milliseconds**, the Fast-Path memory recognizes the campaign signature, inherits the analyst's decision, and blocks it with 100% confidence.
  > 
  > The analyst resolved it once, and the entire organization is protected instantly."

---

### [3:35 – 4:05] 7. BENIGN CORPORATE COMMS (Policy Safety Guardrail)
* **Screen:** Still on `/app/`
* **What to Do:**
  1. Click the green sample button: **`[ 🟢 Benign Comms ]`**.
  2. Point out the subject: *"URGENT: Corporate Annual Benefits Open Enrollment"* from `hr-benefits@company.com`.
  3. Click **`Run Triage`**.
* **What to Show:**
  - Green badge: **`VERIFIED BENIGN / LEGITIMATE`**.
  - Trust score: **`95.0%`**.
* **🎙️ What to Say:**
  > "Finally, what about legitimate internal corporate emails?
  > 
  > Here is an HR announcement about annual benefits. It contains urgency words like 'URGENT' and 'Deadline Friday', which normally confuse standard AI models.
  > 
  > Our machine learning engine is focused on separating spam from phishing. So to prevent false alarms, our **policy guardrail** verifies authentic internal domain authentication and zero threat flags, safely routing it as **`VERIFIED BENIGN`** without polluting our ML retraining data."

---

### [4:05 – 4:25] 8. DATABASE & WRAP-UP
* **Screen:** Switch to third tab: `http://127.0.0.1:8000/app/database` (or stay on `/app/`).
* **What to Show:** Point to the audit log table with the purple campaign badges and the **`Export Audit Log (CSV)`** button.
* **🎙️ What to Say:**
  > "Every decision, human review, and campaign cluster is permanently logged in our audit database and can be exported to CSV for compliance and regulatory reporting.
  > 
  > In summary, our platform stops alert fatigue, cuts 90% of repetitive triage work, and learns from human analysts in under 2 milliseconds.
  > 
  > Thank you for watching!"
