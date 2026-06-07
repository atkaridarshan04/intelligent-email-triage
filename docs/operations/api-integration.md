# API Integration Guide

**Date:** 2026-06-07
**Audience:** SOC platform engineers integrating the triage system into existing tooling

---

## Overview

The system exposes a REST API. It accepts a reported email, returns a routing decision with
confidence score and reasons. No UI is provided or required — the system is designed to be
wired into whatever email security platform, ticketing system, or analyst interface the
client already operates.

Common integration patterns:
- Email gateway (Proofpoint, Mimecast, Defender) forwards reported emails via webhook → `POST /triage`
- SOC ticketing system (ServiceNow, Jira) submits analyst verdicts → `POST /feedback`
- Analyst interface queries the review queue → `GET /feedback/queue`

---

## Base URL

```
https://<deployment-host>/
```

All endpoints return `application/json`.

---

## Endpoints

### `POST /triage`

Submit a reported email for classification. Accepts either a raw `.eml` file or a
pre-parsed JSON object.

**Request — raw .eml (preferred)**

```http
POST /triage
Content-Type: message/rfc822

<raw .eml content>
```

**Request — pre-parsed JSON**

```http
POST /triage
Content-Type: application/json

{
  "subject":    "Urgent: Verify your account",
  "body_text":  "Please click the link below to verify...",
  "from_addr":  "security@paypa1-alerts.com",
  "reply_to":   "reply@gmail.com",
  "to":         "user@company.com",
  "headers":    { "Received": "...", "X-Mailer": "..." },
  "urls":       ["http://paypa1-alerts.com/verify"],
  "attachments": []
}
```

All fields except `subject` and `body_text` are optional. Providing raw `.eml` is preferred
— the parser extracts everything. Pre-parsed JSON is available for platforms that have
already parsed the email.

**Response — auto-classified**

```json
{
  "email_id":            "sha256:a3f9...",
  "label":               "Phishing",
  "predicted_class":     "Phishing",
  "spam_probability":    0.04,
  "phishing_probability": 0.93,
  "trust_score":         91,
  "routed_to_review":    false,
  "reasons": [
    "Credential request language detected",
    "Reply-to mismatch detected",
    "Suspicious URL structure with high entropy"
  ],
  "confidence_notes": [
    "Strong class separation (margin: 0.89)"
  ],
  "model_version": "transformer-v1.0",
  "latency_ms":    187
}
```

**Response — routed to analyst review**

```json
{
  "email_id":            "sha256:c71b...",
  "label":               "Analyst Review",
  "predicted_class":     "Phishing",
  "spam_probability":    0.47,
  "phishing_probability": 0.53,
  "trust_score":         58,
  "routed_to_review":    true,
  "reasons": [
    "Urgency language detected",
    "Free-email sender"
  ],
  "confidence_notes": [
    "Spam and Phishing probabilities too close (margin: 0.06)"
  ],
  "model_version": "transformer-v1.0",
  "latency_ms":    194
}
```

`predicted_class` in a review response is the model's best guess — it tells the analyst
which direction the model leaned, even though confidence was insufficient to automate.

---

### `POST /feedback`

Submit an analyst verdict for a reviewed email. Call this when an analyst confirms,
overrides, or escalates a triage decision.

```http
POST /feedback
Content-Type: application/json

{
  "email_id":      "sha256:c71b...",
  "analyst_label": "Phishing",
  "analyst_id":    "analyst-42",
  "notes":         "BEC pattern — executive impersonation, no URLs"
}
```

`analyst_label` must be one of: `Spam`, `Phishing`, `Escalate`, `Defer`.

`Escalate` — analyst believes this warrants further investigation beyond standard triage.
`Defer` — insufficient information to decide; email stays in review queue.

**Response**

```json
{ "status": "accepted", "email_id": "sha256:c71b..." }
```

---

### `GET /feedback/queue`

Returns emails currently awaiting analyst review, ordered by trust score ascending
(most uncertain first).

```http
GET /feedback/queue?limit=50&offset=0
```

**Response**

```json
{
  "total": 14,
  "items": [
    {
      "email_id":            "sha256:c71b...",
      "received_at":         "2026-06-07T14:32:11Z",
      "predicted_class":     "Phishing",
      "spam_probability":    0.47,
      "phishing_probability": 0.53,
      "trust_score":         58,
      "reasons":             ["Urgency language detected", "Free-email sender"],
      "confidence_notes":    ["Margin too low for automated decision"]
    }
  ]
}
```

---

### `GET /health`

Liveness check.

```json
{ "status": "ok", "model_version": "transformer-v1.0" }
```

---

### `GET /model/info`

```json
{
  "model_version":   "transformer-v1.0",
  "model_type":      "transformer",
  "training_date":   "2026-06-01",
  "dataset_version": "v3.1",
  "metrics": {
    "phishing_recall": 0.9801,
    "accuracy":        0.9762,
    "auto_classify_rate": 0.968
  }
}
```

---

### `GET /metrics`

Prometheus-format operational metrics. Plug into any standard monitoring stack.

```
emails_triaged_total{label="Phishing"} 1482
emails_triaged_total{label="Spam"} 8731
emails_triaged_total{label="Analyst Review"} 312
analyst_review_rate 0.031
override_rate 0.087
inference_latency_ms_p50 188
inference_latency_ms_p99 241
model_version{version="transformer-v1.0"} 1
```

---

## Routing Logic Reference

| Trust Score | Label |
|-------------|-------|
| > 90 | Auto-classify |
| 75 – 90 | Auto-classify (monitoring flag set) |
| 55 – 75 | Analyst Review |
| < 55 | Priority Analyst Review |

**Security override:** If `phishing_probability > 0.70` and a high-weight malicious signal
is present (credential request, typosquatting domain, macro-enabled attachment, IP literal
URL, BEC pattern), the email is escalated as Phishing regardless of trust score.

---

## Integration Notes

**Webhook from email gateway**

Most enterprise email gateways support forwarding reported emails to a webhook URL. Point
the webhook at `POST /triage` with `Content-Type: message/rfc822`. The system handles
parsing entirely.

**Ticketing system integration**

When an analyst closes a ticket for a reviewed email, the ticketing system should call
`POST /feedback` with the analyst's verdict. The `email_id` from the original triage
response is the correlation key. If the ticketing system cannot store arbitrary fields,
store `email_id` in a custom field on the ticket.

**Polling vs push for review queue**

`GET /feedback/queue` is a polling endpoint. If the client's analyst interface supports
webhooks, a lightweight adapter can poll this endpoint on a short interval and push new
items into the interface. There is no built-in push/SSE — it is not needed at the expected
review queue volume.

**No auth is implemented in the system.** Deploy behind the client's existing API gateway,
internal network boundary, or mTLS setup. Do not expose the API publicly without a security
layer in front of it.
