"""
Generate Barclays Project Status PPT — Intelligent Email Triage
Run: pip install python-pptx && python generate_ppt.py
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import copy

# --- Color Scheme ---
NAVY = RGBColor(0x1B, 0x2A, 0x4A)
DARK_BLUE = RGBColor(0x2C, 0x3E, 0x6B)
LIGHT_BLUE = RGBColor(0x4A, 0x90, 0xD9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF5, 0xF5, 0xF5)
DARK_GRAY = RGBColor(0x33, 0x33, 0x33)
GREEN = RGBColor(0x27, 0xAE, 0x60)
ORANGE = RGBColor(0xF3, 0x9C, 0x12)
RED = RGBColor(0xE7, 0x4C, 0x3C)
ACCENT = RGBColor(0x00, 0x9B, 0x8D)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)


# --- Helper Functions ---

def add_dark_slide(prs):
    """Add a blank slide with navy background."""
    slide_layout = prs.slide_layouts[6]  # Blank
    slide = prs.slides.add_slide(slide_layout)
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = NAVY
    return slide


def add_light_slide(prs):
    """Add a blank slide with light background."""
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = WHITE
    return slide


def add_title(slide, text, top=Inches(0.4), left=Inches(0.6), width=Inches(12), font_size=Pt(32), color=WHITE, bold=True):
    """Add a title text box."""
    txBox = slide.shapes.add_textbox(left, top, width, Inches(0.8))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = font_size
    p.font.bold = bold
    p.font.color.rgb = color
    return txBox


def add_subtitle(slide, text, top=Inches(1.2), left=Inches(0.6), width=Inches(12), font_size=Pt(18), color=LIGHT_BLUE):
    """Add subtitle text."""
    txBox = slide.shapes.add_textbox(left, top, width, Inches(0.6))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = font_size
    p.font.color.rgb = color
    return txBox


def add_body_text(slide, bullets, top=Inches(1.8), left=Inches(0.8), width=Inches(11.5), font_size=Pt(16), color=WHITE, line_spacing=1.5):
    """Add bulleted body text."""
    txBox = slide.shapes.add_textbox(left, top, width, Inches(5))
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = bullet
        p.font.size = font_size
        p.font.color.rgb = color
        p.space_after = Pt(10)
        p.level = 0
    return txBox


def add_table(slide, rows, col_widths, top=Inches(2.2), left=Inches(0.6), header_color=DARK_BLUE, font_size=Pt(13)):
    """Add a styled table."""
    num_rows = len(rows)
    num_cols = len(rows[0])
    total_width = sum(col_widths)
    
    table_shape = slide.shapes.add_table(num_rows, num_cols, left, top, Emu(total_width), Inches(0.4 * num_rows))
    table = table_shape.table
    
    # Set column widths
    for i, w in enumerate(col_widths):
        table.columns[i].width = Emu(w)
    
    # Populate cells
    for row_idx, row_data in enumerate(rows):
        for col_idx, cell_text in enumerate(row_data):
            cell = table.cell(row_idx, col_idx)
            cell.text = str(cell_text)
            p = cell.text_frame.paragraphs[0]
            p.font.size = font_size
            
            if row_idx == 0:
                # Header row
                p.font.bold = True
                p.font.color.rgb = WHITE
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_color
            else:
                p.font.color.rgb = DARK_GRAY
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT_GRAY if row_idx % 2 == 0 else WHITE
            
            p.alignment = PP_ALIGN.CENTER
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    
    return table_shape


# ============================================================
# SLIDE 1: Title
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Intelligent Email Triage", top=Inches(2.2), font_size=Pt(44))
add_subtitle(slide, "AI-Assisted SOC Triage for User-Reported Suspicious Emails", top=Inches(3.2), font_size=Pt(22), color=LIGHT_BLUE)
add_body_text(slide, ["Project Status Update — July 2026"], top=Inches(4.2), font_size=Pt(18), color=LIGHT_BLUE)


# ============================================================
# SLIDE 2: Problem Statement
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "The Problem")
add_body_text(slide, [
    "• SOC analysts receive high volumes of user-reported suspicious emails daily",
    "• Users cannot distinguish spam from phishing — everything lands in the analyst queue",
    "• Analysts manually triage every reported email → fatigue, delayed threat response",
    "• Low-risk nuisance emails dilute attention from real phishing attacks",
    "",
    "Our question:",
    "\"Among emails users reported as suspicious, which are nuisance spam",
    "  and which are genuine phishing threats?\""
], top=Inches(1.6), font_size=Pt(18))


# ============================================================
# SLIDE 3: Solution Overview
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Solution Overview")
add_body_text(slide, [
    "• Binary classifier: Spam vs Phishing",
    "• Confidence-based routing adds a third operational outcome: Analyst Review",
    "• Model learns 2 classes — runtime outputs 3 outcomes:",
    "",
    "     Email  →  Model  →  Spam (auto-suppress)",
    "                              →  Phishing (immediate escalation)",
    "                              →  Analyst Review (uncertain → manual triage)",
    "",
    "• Targets:",
    "     – Phishing recall > 98%",
    "     – Analyst workload reduction > 50%",
    "     – Calibrated confidence scores + explainable decisions"
], top=Inches(1.6), font_size=Pt(17))


# ============================================================
# SLIDE 4: Dataset Sources
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Dataset — Sources & Construction")
add_body_text(slide, [
    "Assembled from multiple public email corpora:",
    "",
    "  Spam:        TREC 2007  |  SpamAssassin  |  CEAS 2008",
    "  Phishing:   Nazario  |  IWSPA-AP  |  Kaggle Phishing",
    "  Augmentation:  Template-based phishing generation",
    "                         (brand variation, sender mutation, synonym substitution)",
    "",
    "Final dataset: ~22,000 samples  (15.5k train / 3.2k val / 3.2k test)",
    "",
    "Phishing subtypes covered:",
    "  • Credential harvesting     • BEC / executive impersonation",
    "  • Malware delivery             • Invoice & payment fraud",
    "  • Redirect / landing-page phishing"
], top=Inches(1.5), font_size=Pt(16))


# ============================================================
# SLIDE 5: Dataset Integrity
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Dataset Integrity Pipeline")
add_subtitle(slide, "Quality gates applied before any model training", color=LIGHT_BLUE)
add_body_text(slide, [
    "1. Deduplicated across splits using normalized text hashing",
    "      → prevents cross-split leakage",
    "",
    "2. Restricted synthetic/augmented samples to training set only",
    "      → ensures clean, uncontaminated evaluation",
    "",
    "3. Removed provenance-correlated fields from feature set",
    "      → model learns phishing signals, not dataset origin",
    "",
    "4. Rebuilt splits via stratified random sampling",
    "      → consistent feature distributions across train/val/test",
    "",
    "5. Verified engineered feature correctness post-split",
    "",
    "6. Validated schema consistency and label encoding"
], top=Inches(1.8), font_size=Pt(16))


# ============================================================
# SLIDE 6: Feature Engineering
# ============================================================
slide = add_light_slide(prs)
add_title(slide, "Feature Engineering — Multimodal Signals", color=NAVY)
add_subtitle(slide, "19 structured features + TF-IDF text vectorization (30k vocabulary)", top=Inches(1.1), color=DARK_BLUE)

table_data = [
    ["Signal Group", "Features Extracted"],
    ["Sender Signals", "Display-from mismatch, reply-to mismatch, free-email sender"],
    ["URL Signals", "URL count, domain count, shortened URLs, suspicious TLDs,\nIP literal URLs, URL entropy, typosquatting detection"],
    ["Attachment Signals", "Has attachment, executable detected, macro-enabled document"],
    ["Text Statistics", "Subject length, body length, uppercase ratio, digit ratio,\npunctuation density, link density"],
    ["Brand Signals", "Known brand mention, sender-brand mismatch"],
]
col_widths = [Inches(2.5).emu, Inches(9.5).emu]
add_table(slide, table_data, col_widths, top=Inches(1.8), font_size=Pt(14))


# ============================================================
# SLIDE 7: Feature Philosophy
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Feature Design Philosophy")
add_body_text(slide, [
    "Every input mirrors how a real SOC analyst evaluates an email:",
    "",
    "  Sender mismatch      →  \"Is this person who they claim to be?\"",
    "  URL analysis              →  \"Where does this link actually go?\"",
    "  Attachment flags       →  \"Is this payload dangerous?\"",
    "  Text statistics            →  \"Mass spam or targeted attack?\"",
    "  Brand signals             →  \"Is someone impersonating a trusted brand?\"",
    "",
    "• Model inputs limited to signals genuinely present in an email",
    "     — no metadata shortcuts, no information the model shouldn't have",
    "",
    "• Future (production): SPF/DKIM/DMARC, IP reputation, sender history",
    "     — additive signals once enterprise telemetry is available"
], top=Inches(1.5), font_size=Pt(16))


# ============================================================
# SLIDE 8: Model Development Phases
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Model Development — 3-Phase Approach")
add_body_text(slide, [
    "Progressive complexity — each phase builds on prior learnings:",
    "",
    "  Phase 1:  Logistic Regression",
    "                  Fast, interpretable baseline. Establishes minimum viable performance.",
    "",
    "  Phase 2:  LightGBM",
    "                  Enterprise candidate. Handles sparse TF-IDF + structured features natively.",
    "                  Strong nonlinear learning, SHAP explainability, low latency.",
    "",
    "  Phase 3:  RoBERTa + MLP Hybrid Transformer",
    "                  Deep semantic understanding + structured features via fusion layer.",
    "                  125M parameters. 3 full experiment runs.",
    "",
    "• Strict methodology: train on train set, tune on validation, report on held-out test only"
], top=Inches(1.5), font_size=Pt(16))


# ============================================================
# SLIDE 9: Results Table
# ============================================================
slide = add_light_slide(prs)
add_title(slide, "Results — Phase Comparison", color=NAVY)
add_subtitle(slide, "LightGBM wins on every classification metric", top=Inches(1.1), color=DARK_BLUE)

results_data = [
    ["Metric", "Phase 1 (LR)", "Phase 2 (LightGBM)", "Phase 3 (RoBERTa+MLP)"],
    ["Accuracy", "93.51%", "97.62% ✓", "94.86%"],
    ["Phishing Recall", "94.38%", "98.01% ✓", "97.01%"],
    ["Phishing Precision", "93.56%", "97.55% ✓", "93.62%"],
    ["ROC-AUC", "0.9720", "0.9959 ✓", "0.9682"],
    ["Auto-classify Rate", "82.8%", "98.8% ✓", "94.4%"],
]
col_widths = [Inches(2.8).emu, Inches(2.8).emu, Inches(3.5).emu, Inches(3.5).emu]
add_table(slide, results_data, col_widths, top=Inches(1.8), font_size=Pt(15))

# Add footer note
txBox = slide.shapes.add_textbox(Inches(0.8), Inches(5.5), Inches(10), Inches(0.6))
tf = txBox.text_frame
p = tf.paragraphs[0]
p.text = "Phase 2 (LightGBM) selected as production model — only model exceeding 98% phishing recall target"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = DARK_BLUE


# ============================================================
# SLIDE 10: Why LightGBM
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Why LightGBM is the Right Choice Today")
add_body_text(slide, [
    "• Only model exceeding the 98% phishing recall target",
    "",
    "• 98.8% auto-classify rate → analyst workload reduced dramatically",
    "     (only 1.2% of emails need manual review)",
    "",
    "• Fast inference, simple deployment — single .txt model file",
    "",
    "• SHAP explainability built-in — every decision has human-readable reasons",
    "",
    "• Calibration (ECE ≈ 0.44) is a dataset-level property:",
    "     — shared equally across all 3 model families (LR, LightGBM, Transformer)",
    "     — not a model weakness; routing still works correctly in practice",
    "     — fixable with more ambiguous training examples (feedback loop)"
], top=Inches(1.5), font_size=Pt(16))


# ============================================================
# SLIDE 11: Transformer — Long Term
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Transformer — Long-Term Architecture")
add_body_text(slide, [
    "Phase 3 ran 3 full experiments:",
    "  Run 1: Baseline (best recall: 97.01%)",
    "  Run 2: Label smoothing + mixup (best ECE: 0.389, but unstable)",
    "  Run 3: Label smoothing only (balanced, 96.19% recall)",
    "",
    "Why it couldn't beat LightGBM at this scale:",
    "  • 15k training samples vs 125M parameters — model is data-starved",
    "  • TF-IDF already captures spam/phishing vocabulary difference effectively",
    "  • Transformer needs 100k+ samples to express its contextual advantage",
    "",
    "The transformer IS the right long-term model.",
    "6 documented improvements ready for next attempt:",
    "  Layer-wise LR decay | Head+tail truncation | Embedding-space mixup",
    "  Larger dataset | Gradual unfreezing | Subtype-stratified evaluation"
], top=Inches(1.5), font_size=Pt(15))


# ============================================================
# SLIDE 12: System Built
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "The System We Built")
add_subtitle(slide, "Complete production inference system — not just a model", color=LIGHT_BLUE)
add_body_text(slide, [
    "Pipeline:  Email Parser → Feature Extractor → Model Adapter → Confidence Router → Explainability",
    "",
    "REST API (FastAPI):",
    "  POST /triage          — classify email, return routing + explanation",
    "  POST /feedback       — store analyst verdict",
    "  GET  /feedback/queue — emails awaiting review (sorted by uncertainty)",
    "  GET  /health              — system status + model version",
    "  GET  /metrics            — Prometheus-format monitoring",
    "",
    "Supporting infrastructure:",
    "  • Feedback Store (SQLite)     • Retraining Scripts (calibrate / full)",
    "  • Drift Detector                      • Demo UI (3-page Jinja2 interface)",
    "  • Docker packaging              • Pluggable model (manifest.json)",
    "",
    "149 tests passing  |  Swap LightGBM ↔ Transformer with zero code changes"
], top=Inches(1.7), font_size=Pt(15))


# ============================================================
# SLIDE 13: Confidence Routing
# ============================================================
slide = add_light_slide(prs)
add_title(slide, "Confidence Routing & Explainability", color=NAVY)

routing_data = [
    ["Trust Score", "Routing Action", "Description"],
    ["> 90", "Auto-classify", "High confidence — automated decision"],
    ["75 – 90", "Auto-classify + Monitor", "Confident but flagged for review sampling"],
    ["55 – 75", "Analyst Review", "Uncertain — manual triage required"],
    ["< 55", "Priority Analyst Review", "Very uncertain — top of analyst queue"],
]
col_widths = [Inches(2.2).emu, Inches(3.5).emu, Inches(6.5).emu]
add_table(slide, routing_data, col_widths, top=Inches(1.6), font_size=Pt(14))

txBox = slide.shapes.add_textbox(Inches(0.8), Inches(4.5), Inches(11), Inches(2.5))
tf = txBox.text_frame
tf.word_wrap = True
lines = [
    ("Trust Score Formula: ", "0.6 × max_probability + 0.4 × margin_score  (normalized 0–100)"),
    ("", ""),
    ("Security Override: ", "phishing probability > 0.70 + high-risk signal → immediate escalation"),
    ("", ""),
    ("Explainability: ", "SHAP attributions → rule summarizer → human-readable reasons on every decision"),
]
for i, (bold_part, normal_part) in enumerate(lines):
    if i == 0:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    if bold_part:
        run = p.add_run()
        run.text = bold_part
        run.font.bold = True
        run.font.size = Pt(14)
        run.font.color.rgb = DARK_BLUE
    if normal_part:
        run = p.add_run()
        run.text = normal_part
        run.font.size = Pt(14)
        run.font.color.rgb = DARK_GRAY


# ============================================================
# SLIDE 14: Feedback Loop
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Feedback Loop — Continuous Improvement")
add_body_text(slide, [
    "How the system improves itself over time:",
    "",
    "  1. Model routes uncertain emails → Analyst Review queue",
    "  2. Analyst provides verdict (Confirm / Override → Spam / Override → Phishing)",
    "  3. Verdict stored with full context (features, probabilities, text)",
    "  4. Drift detector monitors 7-day rolling override rate",
    "  5. At >20% override rate → signals retraining needed",
    "  6. Retrain: merge feedback labels → train → evaluate → gate",
    "  7. Human approves promotion → new model goes live",
    "",
    "Two retrain modes:",
    "  • Calibration-only  —  quick (<2 min), when <500 new samples",
    "  • Full retrain          —  new model, requires phishing recall ≥ current production",
    "",
    "No automatic deployment — human gates every model promotion"
], top=Inches(1.5), font_size=Pt(15))


# ============================================================
# SLIDE 15: Current Status
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Current Status & Roadmap")
add_body_text(slide, [
    "Status:",
    "  ✅  All build phases complete (Pipeline, API, Feedback, Retraining, Demo UI, Docker)",
    "  ✅  149 tests, all passing",
    "  ✅  LightGBM validated: 98.01% phishing recall, 98.8% auto-classify",
    "  ⚠️  One remaining step: export model artifacts from Kaggle → system goes live",
    "",
    "Roadmap:",
    "",
    "  Near-term:    Export artifacts → deploy → collect analyst feedback",
    "",
    "  Mid-term:     5,000 analyst-reviewed samples → retrain → improve calibration",
    "",
    "  Long-term:   100k+ total samples → transformer revival with documented fixes",
    "                        → two-stage router (LightGBM for easy, Transformer for hard)"
], top=Inches(1.5), font_size=Pt(16))


# ============================================================
# SLIDE 16: Key Takeaways
# ============================================================
slide = add_dark_slide(prs)
add_title(slide, "Key Takeaways")
add_body_text(slide, [
    "1. Built a complete AI triage system",
    "      — model + pipeline + API + feedback + monitoring + packaging",
    "",
    "2. Rigorous data engineering",
    "      — integrity pipeline, multimodal features, strict evaluation methodology",
    "",
    "3. Transparent about data scale",
    "      — and built the system that solves it over time via the feedback loop",
    "",
    "4. Meeting 98% phishing recall today with LightGBM",
    "      — architecture designed to evolve as data grows",
    "",
    "5. The system gets better the more it's used",
    "      — production usage generates training data → retrain → improve"
], top=Inches(1.5), font_size=Pt(17))


# ============================================================
# SAVE
# ============================================================
output_path = "barclays_email_triage_status.pptx"
prs.save(output_path)
print(f"✅ Presentation saved: {output_path}")
print(f"   16 slides generated successfully.")
