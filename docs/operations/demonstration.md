# Client Demonstration Guide

**Date:** 2026-06-07
**Purpose:** Demo setup and walkthrough for client presentation

---

## What the Demo Needs to Show

1. An email goes in — a routing decision with reasons comes out
2. Uncertain emails land in a review queue, not a forced wrong answer
3. An analyst confirms or overrides — that verdict is stored
4. The system explains *why* it made the decision, not just *what* it decided

That's the whole story. Everything else is detail.

---

## Demo UI

The production system has no UI — it's infrastructure, designed to plug into the client's
existing SOC tooling. For demonstration purposes, a minimal demo UI is built as a separate
artifact. It is a thin skin over the API and is not part of the production codebase.

### Three Pages

**1. Triage Page**
- Drag-and-drop `.eml` upload or paste raw email text
- "Triage" button → calls `POST /triage`
- Result card shows: routing label, trust score, spam/phishing probabilities, reasons list
- If routed to Analyst Review, card shows the model's lean alongside the uncertainty note

**2. Review Queue Page**
- Lists all emails pending analyst review (`GET /feedback/queue`)
- Each row shows: received time, model's predicted class, trust score, top reason
- Ordered most uncertain first
- Click a row to open the verdict page

**3. Verdict Page**
- Full triage result for the selected email
- Confirm / Override / Escalate / Defer buttons
- Override requires selecting the correct label (Spam / Phishing)
- Optional notes field
- Submit → calls `POST /feedback`, removes item from queue, shows updated queue

### Tech

Minimal React frontend or server-rendered HTML served by FastAPI — whichever is faster to
build. No auth, no polish. The point is a clickable walkthrough, not a product.

---

## Demo Script

### Setup

Have three emails ready before the demo:

| Email | Expected outcome | Purpose |
|-------|-----------------|---------|
| Obvious phishing (credential request, typosquatting URL) | Phishing, high trust | Show confident escalation |
| Obvious spam (promotional, unsubscribe link) | Spam, high trust | Show confident auto-suppress |
| Ambiguous (urgency language, free-email sender, no URLs) | Analyst Review | Show the human-in-the-loop |

Use real-looking example emails, not obviously synthetic ones.

### Walkthrough

**Step 1 — Phishing hit**
Upload the phishing email. Show the result: label, trust score ~92, reasons list. Point out
that this would be immediately escalated in a live SOC — no analyst time spent.

**Step 2 — Spam hit**
Upload the spam email. Show auto-suppress result. This is the noise reduction story — the
analyst never sees this email.

**Step 3 — Analyst Review**
Upload the ambiguous email. Show it lands in Analyst Review with the model's lean visible.
Navigate to the Review Queue — show the email sitting there. Open the Verdict page.
Override to Phishing with a note. Submit. Show the queue is now empty.

**Step 4 — The feedback story**
Explain: that verdict is now stored. When the system retrains — on a schedule or when enough
verdicts have accumulated — this email and the analyst's label feed directly into the next
model. The system gets better on exactly the cases it finds hardest, using the client's own
data. No resubmission to us, no retraining fee — they run `python retrain.py`.

---

## Key Points to Land

- **98%+ phishing recall** — fewer than 2 in 100 phishing emails missed at current
  performance on our dataset. On their data, this improves over time.
- **The review queue shrinks over time** — as the model learns from analyst verdicts, fewer
  emails land in the uncertain bucket. Analyst workload decreases continuously.
- **No forced wrong answers** — uncertain cases go to a human. The system never auto-suppresses
  something it isn't confident about.
- **They own the retraining** — the feedback loop and retrain pipeline are part of what we
  hand them. Their proprietary email data stays on their infrastructure and makes their
  model better, not ours.

---

## What Not to Demo

- Calibration (ECE numbers) — not client-facing, too technical for a demo context
- Raw model metrics tables — summarise verbally if asked, don't put them on screen
- The retrain script running — describe it, don't watch a terminal for 20 minutes
