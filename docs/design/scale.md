# Scaling Considerations

**Date:** 2026-06-07
**Status:** Out of scope for v1 — documented for future reference

---

## Current Design Envelope

The v1 engineering system is designed for a single SOC team processing hundreds to low
thousands of emails per day. It runs as a single Docker container, synchronous inference,
single-machine retraining. This is the right design for the stated scope.

---

## Where It Breaks

**Synchronous transformer inference under high concurrency**

A transformer forward pass takes ~100–200ms. FastAPI handles HTTP concurrency, but each
request blocks a thread for that duration. At low volume this is fine. At high concurrency
(hundreds of simultaneous requests) the thread pool exhausts and latency spikes.

Fix: move to async batched inference. Requests accumulate in a short queue (10–50ms),
are batched, and a single GPU forward pass handles the batch. TorchServe or Triton
Inference Server both support dynamic batching out of the box.

**Single-machine retraining**

Retraining on a single machine is sufficient up to ~500k training examples. Beyond that,
training time becomes impractical on CPU. The fix is not distributed training — it is
GPU-accelerated single-machine training (a single A100 handles millions of examples).
Distributed training (multi-GPU, multi-node) is only warranted at dataset scales this
system will not reach in the near term.

**SQLite feedback store**

SQLite handles concurrent reads fine but serialises writes. At high feedback ingestion
rates (many analysts submitting verdicts simultaneously) write contention becomes an issue.
Migration to Postgres resolves this. The schema is identical — this is a one-line config
change.

---

## What Scaling Looks Like (if needed)

| Bottleneck | Threshold | Fix |
|------------|-----------|-----|
| Synchronous inference | > ~50 concurrent requests | Dynamic batching via TorchServe/Triton |
| Feedback store writes | > ~100 concurrent analysts | Migrate SQLite → Postgres |
| Retraining time | > ~500k training examples | GPU-accelerated single-machine training |
| Single container | Multi-region or HA requirement | Kubernetes deployment, horizontal pod autoscaling |

None of these require architectural changes. The model adapter contract, feedback schema,
and retrain pipeline all remain unchanged. Scaling is an infrastructure concern layered on
top of the existing design.

---

## What Does Not Scale Independently

**The retraining pipeline is intentionally human-gated.** Scaling the inference path does
not change this. Automated retraining at scale introduces data poisoning risk that is not
acceptable for a security system regardless of throughput. The human-in-the-loop retrain
approval step stays.
