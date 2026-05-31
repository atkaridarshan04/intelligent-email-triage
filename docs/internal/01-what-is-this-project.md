# 01 — What Is This Project?

## The Real-World Problem

Every day, employees at a company receive suspicious emails. Some are spam — annoying but harmless (newsletters you didn't sign up for, promotional emails, scam lottery emails). Some are phishing — genuinely dangerous emails designed to steal passwords, trick people into sending money, or install malware.

When an employee thinks an email looks suspicious, they report it to the Security Operations Centre (SOC). The SOC is a team of security analysts whose job is to investigate these reports and decide: is this dangerous or not?

The problem: the SOC gets flooded. Hundreds or thousands of reported emails per day. Most of them are just spam — harmless, but the analyst still has to look at each one to confirm that. This wastes enormous amounts of analyst time on low-risk emails, leaving less time for the genuinely dangerous ones.

## The Goal

Build an AI system that automatically triages (sorts) these reported emails into three buckets:

1. **Spam** — harmless, auto-suppress, no analyst needed
2. **Phishing** — dangerous, immediately escalate to the SOC
3. **Analyst Review** — the AI isn't sure, a human should look at this

The system should:
- Catch more than 98% of phishing emails (missing phishing is very bad)
- Reduce analyst workload by more than 50% (auto-handle the easy cases)
- Never make a fully automated decision when it's not confident (route to human instead)

## How the System Works

```
Employee reports suspicious email
         ↓
AI reads the email (subject, body, links, sender info)
         ↓
AI classifies: Spam or Phishing?
         ↓
AI checks: how confident am I?
         ↓
High confidence → Auto-route (Spam suppressed, Phishing escalated)
Low confidence  → Send to Analyst Review queue
```

The AI never pretends to be certain when it isn't. That's the "human-in-the-loop" design — humans stay involved for the hard cases.

## What the AI Learns

The AI is trained on thousands of example emails that have already been labelled as spam or phishing. It learns patterns:
- Phishing emails often say things like "verify your account", "click here", "your password will expire"
- Phishing emails often have suspicious links, mismatched sender addresses, or impersonate known brands
- Spam emails tend to be marketing-style, with lots of links, promotional language

The AI does NOT learn a third category called "Analyst Review". That's not a type of email — it's a routing decision made at runtime based on how confident the AI is.

## Why This Is Hard

- Spam and phishing share a lot of language (both are unsolicited, both want you to click things)
- Phishing emails are deliberately designed to look legitimate
- Attack patterns change over time — new phishing techniques emerge constantly
- Missing a phishing email (false negative) is much worse than flagging a spam email as phishing (false positive)

## The Three Phases of Building the AI

We built the AI in three phases, each more sophisticated than the last:

- **Phase 1:** Simple model (Logistic Regression) — fast to build, establishes a baseline
- **Phase 2:** Better model (LightGBM) — more powerful, better results
- **Phase 3:** Advanced model (RoBERTa transformer) — understands language deeply, best calibration

Each phase is evaluated against the same targets before deciding whether to go further.
