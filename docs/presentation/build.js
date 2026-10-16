const pptxgen = require("pptxgenjs");

// ---------- Palette ----------
const NAVY = "0D1B2A";      // dominant dark
const STEEL = "1B4965";     // secondary dark
const BLUE = "5FA8D3";      // supporting accent (data / positive)
const RED = "EF476F";       // sharp accent (threat / critical)
const LIGHTBG = "F7F9FB";   // content background
const CARDBG = "FFFFFF";
const MUTED = "5B6B7A";
const DARKTEXT = "142433";
const WHITE = "FFFFFF";
const LINE = "E1E7ED";

const TITLE_FONT = "Cambria";
const BODY_FONT = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
const PW = 13.3, PH = 7.5;

// ---------- Helpers ----------
function bgSlide(dark) {
    const s = pres.addSlide();
    s.background = { color: dark ? NAVY : LIGHTBG };
    return s;
}

function footer(s, pageNum, dark) {
    s.addText("INTELLIGENT EMAIL TRIAGE", {
        x: 0.5, y: 7.16, w: 6, h: 0.28, fontFace: BODY_FONT, fontSize: 9,
        color: dark ? "6E8299" : MUTED, charSpacing: 1, isTextBox: true, margin: 0,
    });
    s.addText(String(pageNum), {
        x: PW - 0.9, y: 7.16, w: 0.4, h: 0.28, fontFace: BODY_FONT, fontSize: 9,
        color: dark ? "6E8299" : MUTED, align: "right", isTextBox: true, margin: 0,
    });
}

function title(s, text, opts = {}) {
    s.addText(text, Object.assign({
        x: 0.6, y: 0.45, w: PW - 1.2, h: 0.8, fontFace: TITLE_FONT, bold: true,
        fontSize: 30, color: NAVY, isTextBox: true, margin: 0,
    }, opts));
}

function kicker(s, text, color = STEEL) {
    s.addText(text.toUpperCase(), {
        x: 0.6, y: 0.2, w: PW - 1.2, h: 0.3, fontFace: BODY_FONT, bold: true,
        fontSize: 12, color: color, charSpacing: 1.5, isTextBox: true, margin: 0,
    });
}

function statCard(s, x, y, w, h, num, label, opts = {}) {
    const fill = opts.fill || CARDBG;
    const numColor = opts.numColor || NAVY;
    s.addShape("roundRect", {
        x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: opts.border || LINE, width: 1 },
        shadow: opts.noShadow ? undefined : { type: "outer", color: "9AA7B4", opacity: 0.25, blur: 8, offset: 2, angle: 90 }
    });
    const numH = h * 0.5;
    s.addText(num, {
        x: x + 0.15, y: y + 0.1, w: w - 0.3, h: numH, fontFace: TITLE_FONT, bold: true,
        fontSize: opts.numSize || 30, color: numColor, align: "center", valign: "bottom", isTextBox: true, margin: 0
    });
    s.addText(label, {
        x: x + 0.15, y: y + numH + 0.18, w: w - 0.3, h: h - numH - 0.18 - 0.08, fontFace: BODY_FONT,
        fontSize: opts.labelSize || 11, color: MUTED, align: "center", valign: "top", isTextBox: true, margin: 0
    });
}

function bulletBlock(s, x, y, w, h, items, opts = {}) {
    const arr = items.map((it, i) => {
        const o = {
            text: it, options: {
                bullet: { code: "2022", indent: 18 }, color: opts.color || DARKTEXT,
                fontSize: opts.fontSize || 13, fontFace: BODY_FONT, breakLine: i !== items.length - 1, paraSpaceAfter: opts.spaceAfter || 10
            }
        };
        return o;
    });
    s.addText(arr, { x, y, w, h, isTextBox: true, margin: 0, valign: "top" });
}

function pillHeader(s, x, y, w, text, color) {
    s.addShape("roundRect", { x, y, w, h: 0.42, rectRadius: 0.21, fill: { color }, line: { type: "none" } });
    s.addText(text, {
        x, y, w, h: 0.42, fontFace: BODY_FONT, bold: true, fontSize: 13, color: WHITE,
        align: "center", valign: "middle", isTextBox: true, margin: 0
    });
}

function circleNum(s, x, y, d, num, color, textColor = WHITE, fontSize = 16) {
    s.addShape("ellipse", { x, y, w: d, h: d, fill: { color }, line: { type: "none" } });
    s.addText(String(num), {
        x, y, w: d, h: d, fontFace: TITLE_FONT, bold: true, fontSize,
        color: textColor, align: "center", valign: "middle", isTextBox: true, margin: 0
    });
}

// =====================================================================
// SLIDE 1 — TITLE
// =====================================================================
{
    const s = bgSlide(true);
    // motif: faint network of circles top-right
    const dots = [[10.6, 0.9, 0.05], [11.3, 1.5, 0.035], [10.1, 1.7, 0.03], [11.9, 1.0, 0.04], [12.3, 1.8, 0.05], [10.8, 2.2, 0.03]];
    dots.forEach(([dx, dy, dr]) => s.addShape("ellipse", { x: dx, y: dy, w: dr * 2, h: dr * 2, fill: { color: BLUE }, line: { type: "none" } }));
    s.addShape("line", { x: 10.65, y: 0.95, w: 0.65, h: 0.55, line: { color: BLUE, width: 0.75, transparency: 40 } });
    s.addShape("line", { x: 11.32, y: 1.53, w: 0.58, h: 0.27, line: { color: BLUE, width: 0.75, transparency: 40 } });
    s.addShape("line", { x: 11.9, y: 1.05, w: 0.4, h: 0.75, line: { color: BLUE, width: 0.75, transparency: 40 } });

    s.addText("AI-ASSISTED SOC DEFENSE PLATFORM", {
        x: 0.7, y: 2.5, w: 10, h: 0.4, fontFace: BODY_FONT, bold: true, fontSize: 13,
        color: BLUE, charSpacing: 2, isTextBox: true, margin: 0,
    });
    s.addText("Intelligent Email Triage", {
        x: 0.65, y: 2.9, w: 11.5, h: 1.3, fontFace: TITLE_FONT, bold: true, fontSize: 48,
        color: WHITE, isTextBox: true, margin: 0,
    });
    s.addText("Reframing phishing detection as a triage problem — isolating the exact decision\nboundary where analyst time is wasted, at 98.01% phishing recall.", {
        x: 0.7, y: 4.15, w: 9.6, h: 0.9, fontFace: BODY_FONT, fontSize: 15, color: "C7D3DE",
        isTextBox: true, margin: 0, lineSpacingMultiple: 1.25,
    });

    // metric strip
    const metrics = [["98.01%", "Phishing Recall"], ["97.62%", "Overall Accuracy"], ["11.8 ms", "P95 Inference"], ["98.8%", "Autonomous Triage"]];
    const mw = 2.65, gap = 0.25, startX = 0.7, my = 5.55;
    metrics.forEach((m, i) => {
        const x = startX + i * (mw + gap);
        s.addShape("roundRect", { x, y: my, w: mw, h: 1.15, rectRadius: 0.07, fill: { color: STEEL }, line: { type: "none" } });
        s.addText(m[0], { x, y: my + 0.12, w: mw, h: 0.6, fontFace: TITLE_FONT, bold: true, fontSize: 26, color: RED, align: "center", isTextBox: true, margin: 0 });
        s.addText(m[1], { x, y: my + 0.72, w: mw, h: 0.35, fontFace: BODY_FONT, fontSize: 10.5, color: "C7D3DE", align: "center", isTextBox: true, margin: 0 });
    });
    footer(s, 1, true);
}

// =====================================================================
// SLIDE 2 — THE OPERATIONAL PROBLEM
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 1 · The Operational Problem");
    title(s, "Signal Buried in Noise");

    bulletBlock(s, 0.6, 1.55, 7.1, 5.3, [
        "Perimeter Gateway Blindspots — SEGs like Proofpoint and Microsoft Defender filter known malware, but spear-phishing pretexts and aggressive marketing still reach the inbox.",
        "Employee Over-Reporting — security awareness training tells staff to report anything unusual, flooding the queue with harmless mail.",
        "Tier-1 Queue Bottleneck — every submission requires manual header inspection, URL decoding, and sandbox detonation.",
        "Alert Fatigue & Threat Dilution — sorting benign marketing mail burns out analysts while real spear-phishing sits buried beneath the noise.",
    ], { fontSize: 14, spaceAfter: 16 });

    // Right stat panel
    s.addShape("roundRect", { x: 8.05, y: 1.55, w: 4.65, h: 5.3, rectRadius: 0.1, fill: { color: NAVY }, line: { type: "none" } });
    s.addText("OF USER-REPORTED EMAIL", {
        x: 8.3, y: 1.95, w: 4.15, h: 0.3, fontFace: BODY_FONT, bold: true, fontSize: 11,
        color: BLUE, charSpacing: 1.2, align: "center", isTextBox: true, margin: 0
    });
    s.addText("85%", {
        x: 8.3, y: 2.2, w: 4.15, h: 1.4, fontFace: BODY_FONT, bold: true, fontSize: 66,
        color: RED, align: "center", isTextBox: true, margin: 0
    });
    s.addText("or more, by internal review", {
        x: 8.3, y: 3.35, w: 4.15, h: 0.3, fontFace: BODY_FONT, italic: true, fontSize: 10.5,
        color: "9FB2C4", align: "center", isTextBox: true, margin: 0
    });
    s.addText("is harmless commercial marketing spam, bulk newsletters, or routine notifications — not a real threat.", {
        x: 8.55, y: 3.8, w: 3.65, h: 1.0, fontFace: BODY_FONT, fontSize: 13, color: "C7D3DE", align: "center", isTextBox: true, margin: 0,
    });
    s.addShape("line", { x: 8.55, y: 4.95, w: 3.65, h: 0, line: { color: "2C4157", width: 1 } });
    s.addText("The result: SOC analysts spend the majority of their time clearing noise instead of hunting real threats.", {
        x: 8.55, y: 5.2, w: 3.65, h: 1.5, fontFace: BODY_FONT, italic: true, fontSize: 12.5, color: "9FB2C4", align: "center", isTextBox: true, margin: 0,
    });
    footer(s, 2, false);
}

// =====================================================================
// SLIDE 3 — STRATEGIC ML THESIS
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 1 · Strategic Thesis");
    title(s, "A Reframed Question Unlocks Precision");

    const colW = 5.85, colY = 1.65, colH = 3.9, gap = 0.4;
    // Flawed
    pillHeader(s, 0.6, colY, colW, "THE CONVENTIONAL FORMULATION", MUTED);
    s.addShape("roundRect", { x: 0.6, y: colY + 0.55, w: colW, h: colH - 0.55, rectRadius: 0.08, fill: { color: CARDBG }, line: { color: LINE, width: 1 } });
    s.addText('"Is this inbound email legitimate corporate mail or malicious?"', {
        x: 0.9, y: colY + 0.8, w: colW - 0.6, h: 0.95, fontFace: TITLE_FONT, italic: true, bold: true, fontSize: 15, color: DARKTEXT, isTextBox: true, margin: 0,
    });
    s.addText("Why it fails: attempts to model the entire distribution of normal corporate communication across millions of employees — the false-positive surface is enormous.", {
        x: 0.9, y: colY + 1.85, w: colW - 0.6, h: 1.9, fontFace: BODY_FONT, fontSize: 13, color: MUTED, isTextBox: true, margin: 0,
    });

    // Reframed
    const x2 = 0.6 + colW + gap;
    pillHeader(s, x2, colY, colW, "OUR REFRAMED FORMULATION", STEEL);
    s.addShape("roundRect", { x: x2, y: colY + 0.55, w: colW, h: colH - 0.55, rectRadius: 0.08, fill: { color: NAVY }, line: { type: "none" } });
    s.addText('"Among emails employees already flagged as suspicious, which are nuisance spam and which are genuine phishing threats?"', {
        x: x2 + 0.3, y: colY + 0.8, w: colW - 0.6, h: 1.15, fontFace: TITLE_FONT, italic: true, bold: true, fontSize: 15, color: WHITE, isTextBox: true, margin: 0,
    });
    s.addText("Operational impact: narrowing scope to user-reported mail eliminates baseline corporate noise and isolates the exact boundary where analyst time is wasted.", {
        x: x2 + 0.3, y: colY + 2.05, w: colW - 0.6, h: 1.7, fontFace: BODY_FONT, fontSize: 13, color: "C7D3DE", isTextBox: true, margin: 0,
    });

    statCard(s, 0.6, 5.85, colW * 2 + gap, 1.05, "98.01% Phishing Recall", "unlocked by narrowing the decision scope", { numSize: 24, numColor: RED, fill: WHITE });
    footer(s, 3, false);
}

// =====================================================================
// SLIDE 4 — ARCHITECTURE PRINCIPLE / DATAFLOW
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 1 · Architecture Principle");
    title(s, "2-Class Model, 3 Operational Outcomes");

    bulletBlock(s, 0.6, 1.45, 12.1, 1.6, [
        "Pure binary learning on Spam vs. Phishing only — no artificial \"Ambiguous\" label, which would introduce noise and blur decision boundaries.",
        "Analyst Review is an emergent runtime decision, triggered by the Confidence Layer on borderline predictions — not a trained class.",
    ], { fontSize: 13, spaceAfter: 6 });

    // -----------------------------------------------------------------
    // Dataflow diagram
    // -----------------------------------------------------------------
    // Shifted down slightly to create more breathing room above.
    const dy = 3.75, dh = 1.15;

    // User-reported email
    s.addShape("roundRect", {
        x: 0.6,
        y: dy,
        w: 2.3,
        h: dh,
        rectRadius: 0.08,
        fill: { color: NAVY },
        line: { type: "none" }
    });

    s.addText("User-Reported\nEmail", {
        x: 0.6,
        y: dy,
        w: 2.3,
        h: dh,
        fontFace: BODY_FONT,
        bold: true,
        fontSize: 14,
        color: WHITE,
        align: "center",
        valign: "middle",
        isTextBox: true,
        margin: 0
    });

    // Input arrow
    s.addShape("rightArrow", {
        x: 3.05,
        y: dy + dh / 2 - 0.13,
        w: 0.55,
        h: 0.26,
        fill: { color: MUTED },
        line: { type: "none" }
    });

    // Triage model + confidence layer
    s.addShape("roundRect", {
        x: 3.75,
        y: dy - 0.15,
        w: 2.5,
        h: dh + 0.3,
        rectRadius: 0.08,
        fill: { color: STEEL },
        line: { type: "none" }
    });

    s.addText("Triage Model\n+ Confidence Layer", {
        x: 3.75,
        y: dy - 0.15,
        w: 2.5,
        h: dh + 0.3,
        fontFace: BODY_FONT,
        bold: true,
        fontSize: 14,
        color: WHITE,
        align: "center",
        valign: "middle",
        isTextBox: true,
        margin: 0
    });

    // -----------------------------------------------------------------
    // Three-way operational branch
    // -----------------------------------------------------------------
    const branchX = 6.6;
    const spineX = branchX + 0.5;
    const modelCenterY = dy + dh / 2;
    const outH = 1.05;

    // Uniform 1.30" spacing between outcome boxes.
    // Middle outcome center is exactly aligned with model center.
    const outcomes = [
        {
            y: 2.5,
            label: "Auto-Suppress",
            sub: "High-confidence Spam",
            color: BLUE
        },
        {
            y: 3.8,
            label: "Tier-2 Analyst\nReview Queue",
            sub: "Borderline predictions",
            color: MUTED
        },
        {
            y: 5.1,
            label: "Escalate & Block",
            sub: "High-confidence Phishing",
            color: RED
        },
    ];

    // Model output → branching spine
    s.addShape("line", {
        x: branchX,
        y: modelCenterY,
        w: 0.5,
        h: 0,
        line: { color: MUTED, width: 2 }
    });

    // Single continuous vertical spine
    const topCenterY = outcomes[0].y + outH / 2;
    const bottomCenterY = outcomes[2].y + outH / 2;

    s.addShape("line", {
        x: spineX,
        y: topCenterY,
        w: 0,
        h: bottomCenterY - topCenterY,
        line: { color: MUTED, width: 1.5 }
    });

    // Outcome branches
    outcomes.forEach(o => {
        const centerY = o.y + outH / 2;

        // Spine → outcome
        s.addShape("line", {
            x: spineX,
            y: centerY,
            w: 0.55,
            h: 0,
            line: { color: MUTED, width: 1.5 }
        });

        // Outcome box
        s.addShape("roundRect", {
            x: 7.65,
            y: o.y,
            w: 2.55,
            h: outH,
            rectRadius: 0.08,
            fill: { color: WHITE },
            line: { color: o.color, width: 2 }
        });

        // Outcome title
        s.addText(o.label, {
            x: 7.85,
            y: o.y + 0.1,
            w: 2.15,
            h: 0.55,
            fontFace: BODY_FONT,
            bold: true,
            fontSize: 13,
            color: NAVY,
            isTextBox: true,
            margin: 0,
            valign: "middle"
        });

        // Outcome description
        s.addText(o.sub, {
            x: 7.85,
            y: o.y + 0.65,
            w: 2.15,
            h: 0.32,
            fontFace: BODY_FONT,
            fontSize: 10,
            color: MUTED,
            isTextBox: true,
            margin: 0
        });

        // Outcome arrow
        s.addShape("rightArrow", {
            x: 10.35,
            y: centerY - 0.12,
            w: 0.4,
            h: 0.24,
            fill: { color: o.color },
            line: { type: "none" }
        });

        // Operational action
        s.addText(
            o.label.includes("Review")
                ? "Analyst"
                : (o.color === RED ? "Block" : "Suppress"),
            {
                x: 10.85,
                y: o.y,
                w: 1.85,
                h: outH,
                fontFace: BODY_FONT,
                italic: true,
                fontSize: 11,
                color: MUTED,
                valign: "middle",
                isTextBox: true,
                margin: 0
            }
        );
    });

    // -----------------------------------------------------------------
    // Non-negotiable targets
    // -----------------------------------------------------------------
    statCard(
        s,
        0.6,
        6.35,
        5.9,
        0.85,
        "\u2265 98.0%",
        "Phishing Recall — Non-Negotiable Target",
        {
            numSize: 22,
            numColor: RED,
            numLabel: true,
            labelSize: 10
        }
    );

    statCard(
        s,
        6.75,
        6.35,
        5.9,
        0.85,
        "> 50%",
        "Analyst Workload Reduction — Non-Negotiable Target",
        {
            numSize: 22,
            numColor: BLUE,
            labelSize: 10
        }
    );

    footer(s, 4, false);
}

// =====================================================================
// SLIDE 5 — DATASET CORPUS & SOURCES
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 2 · Dataset Construction");
    title(s, "21,860 Clean Emails, Five Sources");

    // Donut chart for splits
    s.addChart("doughnut", [{
        name: "Split", labels: ["Training (70.8%)", "Validation (14.6%)", "Test Holdout (14.6%)"],
        values: [15483, 3188, 3189],
    }], {
        x: 0.5, y: 1.55, w: 5.1, h: 4.3, holeSize: 60,
        chartColors: [STEEL, BLUE, RED], showLegend: true, legendPos: "b", legendFontSize: 11,
        showTitle: true, title: "Corpus Split (21,860 Total)", titleFontSize: 14, titleColor: NAVY,
        showValue: false, showPercent: true, dataLabelFontSize: 11, dataLabelColor: WHITE,
        chartArea: { fill: { color: LIGHTBG } }, dataLabelPosition: "outEnd",
    });
    s.addText("100% uncontaminated test holdout — 3,189 real-world samples never seen during training or tuning.", {
        x: 0.6, y: 5.95, w: 5.0, h: 0.6, fontFace: BODY_FONT, italic: true, fontSize: 11.5, color: MUTED, isTextBox: true, margin: 0,
    });

    // Sources list
    const sources = [
        ["Nazario Phishing Corpus", "~5,200", "Academic gold standard for credential harvesting & spear-phishing lures"],
        ["IWSPA-AP 2018 / 2020", "~4,800", "Real enterprise social engineering & targeted credential capture"],
        ["TREC 2007 Public Corpus", "~6,000", "High-volume commercial marketing spam & bulk newsletters"],
        ["SpamAssassin & CEAS 2008", "~4,500", "Standardized nuisance mail & benign transactional alerts"],
        ["Synthetic Augmentation", "~1,360", "Training-only: brand mutations, typosquatting, wire-fraud lures"],
    ];
    let sy = 1.5;
    sources.forEach((row, i) => {
        s.addShape("roundRect", { x: 6.05, y: sy, w: 6.65, h: 0.92, rectRadius: 0.06, fill: { color: CARDBG }, line: { color: LINE, width: 1 } });
        s.addText(row[0], { x: 6.25, y: sy + 0.08, w: 3.9, h: 0.4, fontFace: BODY_FONT, bold: true, fontSize: 12.5, color: DARKTEXT, isTextBox: true, margin: 0 });
        s.addText(row[2], { x: 6.25, y: sy + 0.45, w: 3.9, h: 0.42, fontFace: BODY_FONT, fontSize: 9.5, color: MUTED, isTextBox: true, margin: 0 });
        s.addText(row[1], { x: 10.3, y: sy, w: 2.2, h: 0.92, fontFace: TITLE_FONT, bold: true, fontSize: 17, color: i === 4 ? RED : STEEL, align: "center", valign: "middle", isTextBox: true, margin: 0 });
        sy += 1.02;
    });
    footer(s, 5, false);
}

// =====================================================================
// SLIDE 6 — DATA SCARCITY REALITY
// =====================================================================
{
    const s = bgSlide(true);
    kicker(s, "Module 2 · Transparent Disclosure", BLUE);
    title(s, "The Industry Data Scarcity Reality", { color: WHITE });

    bulletBlock(s, 0.6, 1.6, 7.0, 4.6, [
        "Real enterprise phishing attacks contain active exploits, sensitive customer PII, corporate credentials, and classified threat intelligence — organizations cannot legally release live phishing streams.",
        "In academic and open-source research, organic verified phishing corpora top out at 5,000\u20138,000 unique samples.",
        "A ~22,000-email dataset is the realistic public ceiling. This constraint directly informed our modeling strategy.",
    ], { fontSize: 14.5, color: "D7E1E9", spaceAfter: 18 });

    s.addShape("roundRect", { x: 0.6, y: 5.55, w: 7.0, h: 1.35, rectRadius: 0.08, fill: { color: STEEL }, line: { type: "none" } });
    s.addText("Strategic implication: this ceiling explains why gradient-boosted trees outperformed 125M-parameter transformers — and why a closed-loop feedback system is necessary to scale past it.", {
        x: 0.85, y: 5.65, w: 6.5, h: 1.15, fontFace: BODY_FONT, italic: true, fontSize: 12.5, color: WHITE, valign: "middle", isTextBox: true, margin: 0,
    });

    // Right: ceiling visual — bar comparing public ceiling vs our corpus
    s.addShape("roundRect", { x: 8.1, y: 1.6, w: 4.6, h: 5.3, rectRadius: 0.1, fill: { color: "132A3D" }, line: { type: "none" } });
    s.addText("PUBLIC PHISHING CEILING", { x: 8.35, y: 1.9, w: 4.1, h: 0.3, fontFace: BODY_FONT, bold: true, fontSize: 11, color: BLUE, charSpacing: 1, align: "center", isTextBox: true, margin: 0 });
    s.addText("5,000\u20138,000", { x: 8.35, y: 2.15, w: 4.1, h: 0.9, fontFace: TITLE_FONT, bold: true, fontSize: 34, color: WHITE, align: "center", isTextBox: true, margin: 0 });
    s.addText("organic samples, industry-wide", { x: 8.35, y: 2.95, w: 4.1, h: 0.35, fontFace: BODY_FONT, fontSize: 11, color: "9FB2C4", align: "center", isTextBox: true, margin: 0 });

    s.addShape("line", { x: 8.6, y: 3.5, w: 3.6, h: 0, line: { color: "2C4157", width: 1 } });

    s.addText("OUR CLEAN CORPUS", { x: 8.35, y: 3.7, w: 4.1, h: 0.3, fontFace: BODY_FONT, bold: true, fontSize: 11, color: RED, charSpacing: 1, align: "center", isTextBox: true, margin: 0 });
    s.addText("21,860", { x: 8.35, y: 3.95, w: 4.1, h: 0.9, fontFace: TITLE_FONT, bold: true, fontSize: 34, color: WHITE, align: "center", isTextBox: true, margin: 0 });
    s.addText("emails via multi-source aggregation\n+ targeted synthetic augmentation", { x: 8.35, y: 4.75, w: 4.1, h: 0.6, fontFace: BODY_FONT, fontSize: 11, color: "9FB2C4", align: "center", isTextBox: true, margin: 0 });
    footer(s, 6, true);
}

// =====================================================================
// SLIDE 7 — SIX INTEGRITY GATES
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 2 · Dataset Quality");
    title(s, "Six Proactive Dataset Integrity Gates");

    const gates = [
        ["Cross-Split Deduplication", "SHA-256 hashing purged 100% of duplicate emails across train/val/test."],
        ["Synthetic Data Quarantine", "Augmented attacks restricted strictly to training — zero in val/test."],
        ["Provenance Leakage Removal", "Stripped internal tags & source IDs so models can't take shortcuts."],
        ["Stratified Class & Length Splits", "Balanced class ratios and length distributions across partitions."],
        ["Post-Split Feature Verification", "Engineered extractors run deterministically without split leakage."],
        ["Production Schema Consistency", "MIME parser output matches live production data streams exactly."],
    ];
    const cw = 3.95, ch = 2.35, gx = 0.25, gy = 0.25, ox = 0.6, oy = 1.55;
    gates.forEach((g, i) => {
        const col = i % 3, row = Math.floor(i / 3);
        const x = ox + col * (cw + gx), y = oy + row * (ch + gy);
        s.addShape("roundRect", {
            x, y, w: cw, h: ch, rectRadius: 0.08, fill: { color: CARDBG }, line: { color: LINE, width: 1 },
            shadow: { type: "outer", color: "9AA7B4", opacity: 0.2, blur: 6, offset: 2, angle: 90 }
        });
        circleNum(s, x + 0.25, y + 0.25, 0.55, i + 1, i < 5 ? STEEL : RED, WHITE, 18);
        s.addText(g[0], { x: x + 0.95, y: y + 0.22, w: cw - 1.15, h: 0.65, fontFace: BODY_FONT, bold: true, fontSize: 13, color: DARKTEXT, valign: "top", isTextBox: true, margin: 0 });
        s.addText(g[1], { x: x + 0.25, y: y + 1.0, w: cw - 0.5, h: 1.2, fontFace: BODY_FONT, fontSize: 11, color: MUTED, isTextBox: true, margin: 0 });
    });
    footer(s, 7, false);
}

// =====================================================================
// SLIDE 8 — FEATURE ENGINEERING
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 3 · Feature Engineering");
    title(s, "19 Security Signals + 50,000 Lexical Features");

    s.addText("Pure text models miss structural signals (weaponized attachments, spoofed names); pure rule engines miss semantic nuance. We fuse both to mirror how a Tier-1 analyst reads an email.", {
        x: 0.6, y: 1.45, w: 12.1, h: 0.55, fontFace: BODY_FONT, italic: true, fontSize: 12.5, color: MUTED, isTextBox: true, margin: 0,
    });

    const cats = [
        ["Sender Structure", "display_from_mismatch \u00b7 reply_to_mismatch \u00b7 free_email_sender", "Detects spoofed executive names and external webmail routing."],
        ["URL & Host Threat", "url_entropy \u00b7 typosquatting \u00b7 ip_literal_url \u00b7 suspicious_tld", "Shannon entropy flags DGA domains; Levenshtein flags brand typosquatting."],
        ["Payload & Threat", "has_attachment \u00b7 executable_detected \u00b7 macro_detected", "Identifies weaponized payloads; triggers hard overrides regardless of body text."],
        ["Text Statistics", "body_length \u00b7 uppercase_ratio \u00b7 punctuation_density \u00b7 link_density", "Captures urgency capitalization and unusual link density."],
        ["Brand Abuse", "brand_mention \u00b7 sender_brand_mismatch", "Cross-references mentioned brands against authenticated sender domains."],
    ];
    let cy = 2.05;
    const rh = 0.72;
    cats.forEach((c, i) => {
        s.addShape("roundRect", { x: 0.6, y: cy, w: 12.1, h: rh, rectRadius: 0.05, fill: { color: i % 2 === 0 ? CARDBG : "EEF2F6" }, line: { color: LINE, width: 1 } });
        s.addText(c[0], { x: 0.9, y: cy, w: 2.35, h: rh, fontFace: BODY_FONT, bold: true, fontSize: 12.5, color: NAVY, valign: "middle", isTextBox: true, margin: 0 });
        s.addText(c[1], { x: 3.35, y: cy, w: 4.5, h: rh, fontFace: "Courier New", fontSize: 9.5, color: STEEL, valign: "middle", isTextBox: true, margin: 0 });
        s.addText(c[2], { x: 7.95, y: cy, w: 4.6, h: rh, fontFace: BODY_FONT, fontSize: 10.5, color: MUTED, valign: "middle", isTextBox: true, margin: 0 });
        cy += rh + 0.08;
    });

    s.addText("Lexical layer: 50,000 unigram/bigram TF-IDF features with sublinear scaling 1 + log(tf) — dampens repeated words in disclaimers, highlights rare high-intent phishing terms.", {
        x: 0.6, y: cy + 0.08, w: 12.1, h: 0.45, fontFace: BODY_FONT, italic: true, fontSize: 11, color: RED, isTextBox: true, margin: 0,
    });
    footer(s, 8, false);
}

// =====================================================================
// SLIDE 9 — TREESHAP FEATURE IMPORTANCE
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 3 · Explainability");
    title(s, "TreeSHAP: What Drives Every Decision");

    const labels = ["body_length", "url_entropy", "display_from_mismatch", "brand_mention", "sender_brand_mismatch", "uppercase_ratio"];
    const values = [100, 87, 76, 68, 61, 54]; // relative illustrative ranking magnitude, descending
    s.addChart("bar", [{ name: "Relative TreeSHAP Impact", labels: labels.slice().reverse(), values: values.slice().reverse() }], {
        x: 0.6, y: 1.5, w: 8.2, h: 5.35, barDir: "bar",
        chartColors: [STEEL], invertedColors: [STEEL],
        showTitle: false, showLegend: false, showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: DARKTEXT,
        catAxisLabelFontSize: 11, catAxisLabelColor: DARKTEXT, valAxisHidden: true,
        barGapWidthPct: 40, chartArea: { fill: { color: LIGHTBG } }, plotArea: { fill: { color: LIGHTBG } },
        catGridLine: { style: "none" }, valGridLine: { style: "none" },
    });

    s.addText("TOP DRIVERS, RANKED", { x: 9.1, y: 1.55, w: 3.6, h: 0.3, fontFace: BODY_FONT, bold: true, fontSize: 11, color: STEEL, charSpacing: 1, isTextBox: true, margin: 0 });
    const cats2 = [
        ["1. body_length", "Text Statistic"], ["2. url_entropy", "Network Threat"], ["3. display_from_mismatch", "Sender Structure"],
        ["4. brand_mention", "Brand Abuse"], ["5. sender_brand_mismatch", "Brand Abuse"], ["6. uppercase_ratio", "Text Statistic"],
    ];
    let ly = 1.95;
    cats2.forEach(c => {
        s.addText(c[0], { x: 9.1, y: ly, w: 3.6, h: 0.3, fontFace: BODY_FONT, bold: true, fontSize: 12, color: DARKTEXT, isTextBox: true, margin: 0 });
        s.addText(c[1], { x: 9.1, y: ly + 0.28, w: 3.6, h: 0.28, fontFace: BODY_FONT, fontSize: 9.5, color: MUTED, isTextBox: true, margin: 0 });
        ly += 0.68;
    });
    s.addText("Real-time marginal feature attribution — every ticket ships with a plain-language justification.", {
        x: 9.1, y: ly + 0.1, w: 3.6, h: 0.8, fontFace: BODY_FONT, italic: true, fontSize: 10, color: MUTED, isTextBox: true, margin: 0,
    });
    footer(s, 9, false);
}

// =====================================================================
// SLIDE 10 — 3-PHASE MODEL PROGRESSION / BENCHMARK
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 4 · Benchmark Truth");
    title(s, "Three Model Paradigms, One Uncontaminated Test");

    s.addChart("bar", [
        { name: "Phishing Recall", labels: ["Logistic Regression", "LightGBM (Champion)", "RoBERTa Hybrid"], values: [94.38, 98.01, 97.01] },
        { name: "Overall Accuracy", labels: ["Logistic Regression", "LightGBM (Champion)", "RoBERTa Hybrid"], values: [94.40, 97.62, 94.86] },
        { name: "Phishing Precision", labels: ["Logistic Regression", "LightGBM (Champion)", "RoBERTa Hybrid"], values: [93.56, 97.55, 93.62] },
    ], {
        x: 0.6, y: 1.55, w: 12.1, h: 4.35, barDir: "col", barGrouping: "clustered",
        chartColors: [MUTED, RED, BLUE], showTitle: false, showLegend: true, legendPos: "t", legendFontSize: 11,
        showValue: true, dataLabelFontSize: 8.5, dataLabelPosition: "outEnd", dataLabelColor: DARKTEXT,
        catAxisLabelFontSize: 11.5, catAxisLabelColor: DARKTEXT, valAxisLabelFontSize: 10, valAxisLabelColor: MUTED,
        valAxisMinVal: 90, valAxisMaxVal: 100, valAxisTitle: "Percent (%)", showValAxisTitle: true, valAxisTitleFontSize: 10,
        catGridLine: { style: "none" }, valGridLine: { color: LINE, size: 1 },
        chartArea: { fill: { color: LIGHTBG } }, plotArea: { fill: { color: LIGHTBG } },
    });
    s.addShape("line", { x: 0.6, y: 1.55 + 4.35 * ((100 - 98.0) / 10) * 0.86 + 0.16, w: 12.1, h: 0, line: { color: RED, width: 1.25, dashType: "dash" } });
    s.addText("98.0% Phishing Recall Gate", { x: 10.6, y: 1.55 + 4.35 * ((100 - 98.0) / 10) * 0.86 - 0.14, w: 2.1, h: 0.25, fontFace: BODY_FONT, italic: true, bold: true, fontSize: 9, color: RED, isTextBox: true, margin: 0 });

    const scorecard = [
        ["Autonomous Triage", "82.8%", "98.8%", "94.4%"],
        ["Analyst Review Rate", "17.2%", "1.2%", "5.6%"],
        ["P95 Latency (CPU)", "~4 ms", "~11.8 ms", "~510 ms"],
    ];
    let ty = 6.05;
    const colX = [0.6, 2.75, 5.95, 9.45], colW2 = [2.05, 2.3, 2.4, 2.4], colAlign = ["left", "center", "center", "center"];
    scorecard.forEach((row, ri) => {
        row.forEach((cell, ci) => {
            s.addText(cell, {
                x: colX[ci], y: ty, w: colW2[ci], h: 0.32, fontFace: ci === 0 ? BODY_FONT : "Courier New", bold: ci === 0, fontSize: 10.5,
                color: ci === 2 ? RED : DARKTEXT, align: colAlign[ci], isTextBox: true, margin: 0
            });
        });
        ty += 0.34;
    });
    footer(s, 10, false);
}

// =====================================================================
// SLIDE 11 — MODEL SELECTION DECISION
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 5 · Selection Decision");
    title(s, "Why LightGBM Is the Production Champion");

    const reasons = [
        ["Safety & Compliance", "Only candidate crossing the mandatory 98.0% recall gate (98.01%) — false negatives carry catastrophic enterprise risk."],
        ["Workload Compression", "98.8% autonomous triage rate leaves just 1.2% of volume for manual review."],
        ["Computational Efficiency", "11.8ms on standard CPU hardware — no dedicated GPU clustering required."],
        ["Deterministic Explainability", "Millisecond TreeSHAP attribution for every ticket, satisfying regulatory governance."],
    ];
    const cw = 5.85, ch = 1.75, gx = 0.4, gy = 0.3, ox = 0.6, oy = 1.55;
    reasons.forEach((r, i) => {
        const col = i % 2, row = Math.floor(i / 2);
        const x = ox + col * (cw + gx), y = oy + row * (ch + gy);
        s.addShape("roundRect", {
            x, y, w: cw, h: ch, rectRadius: 0.08, fill: { color: CARDBG }, line: { color: LINE, width: 1 },
            shadow: { type: "outer", color: "9AA7B4", opacity: 0.2, blur: 6, offset: 2, angle: 90 }
        });
        circleNum(s, x + 0.28, y + 0.28, 0.5, i + 1, STEEL, WHITE, 16);
        s.addText(r[0], { x: x + 1.0, y: y + 0.22, w: cw - 1.2, h: 0.5, fontFace: BODY_FONT, bold: true, fontSize: 14, color: NAVY, isTextBox: true, margin: 0 });
        s.addText(r[1], { x: x + 0.28, y: y + 0.85, w: cw - 0.56, h: 0.8, fontFace: BODY_FONT, fontSize: 11, color: MUTED, isTextBox: true, margin: 0 });
    });

    s.addShape("roundRect", { x: 0.6, y: 6.05, w: 12.1, h: 1.0, rectRadius: 0.08, fill: { color: NAVY }, line: { type: "none" } });
    s.addText("Calibration disclosure: ", { x: 0.85, y: 6.1, w: 2.3, h: 0.9, fontFace: BODY_FONT, bold: true, fontSize: 11.5, color: RED, valign: "middle", isTextBox: true, margin: 0 });
    s.addText("ECE sits at ~0.44 across all three models — spam/phishing vocabulary is hyper-separable, so cross-entropy pushes probabilities to extremes. Discriminative sorting is near-perfect (ROC-AUC 0.9845); the composite Trust Score, not raw probability, governs routing.", {
        x: 3.05, y: 6.1, w: 9.4, h: 0.9, fontFace: BODY_FONT, fontSize: 11, color: "D7E1E9", valign: "middle", isTextBox: true, margin: 0,
    });
    footer(s, 11, false);
}

// =====================================================================
// SLIDE 12 — TRUST SCORE FORMULA
// =====================================================================
{
    const s = bgSlide(true);
    kicker(s, "Module 6 · Confidence Routing", BLUE);
    title(s, "The Dual-Signal Trust Score", { color: WHITE });

    s.addText("Raw model probabilities cannot be trusted as absolute confidence due to calibration error. We combine maximum probability with prediction margin.", {
        x: 0.6, y: 1.5, w: 12.1, h: 0.55, fontFace: BODY_FONT, italic: true, fontSize: 13, color: "C7D3DE", isTextBox: true, margin: 0,
    });

    s.addShape("roundRect", { x: 1.4, y: 2.3, w: 10.5, h: 1.5, rectRadius: 0.1, fill: { color: STEEL }, line: { type: "none" } });
    s.addText([
        { text: "Trust Score = ", options: { color: WHITE, bold: true } },
        { text: "( 0.60 \u00d7 max(P", options: { color: BLUE, bold: true } },
        { text: "phish", options: { color: BLUE, bold: true, fontSize: 14 } },
        { text: ", P", options: { color: BLUE, bold: true } },
        { text: "spam", options: { color: BLUE, bold: true, fontSize: 14 } },
        { text: ") + 0.40 \u00d7 |P", options: { color: BLUE, bold: true } },
        { text: "phish", options: { color: BLUE, bold: true, fontSize: 14 } },
        { text: " \u2212 P", options: { color: BLUE, bold: true } },
        { text: "spam", options: { color: BLUE, bold: true, fontSize: 14 } },
        { text: "| ) \u00d7 100", options: { color: BLUE, bold: true } },
    ], { x: 1.6, y: 2.3, w: 10.1, h: 1.5, fontFace: "Cambria", fontSize: 22, align: "center", valign: "middle", isTextBox: true, margin: 0 });

    const boxW = 5.7;
    s.addShape("roundRect", { x: 0.6, y: 4.15, w: boxW, h: 2.7, rectRadius: 0.08, fill: { color: "132A3D" }, line: { type: "none" } });
    s.addText("MAX PROBABILITY", { x: 0.85, y: 4.35, w: boxW - 0.5, h: 0.3, fontFace: BODY_FONT, bold: true, fontSize: 12, color: BLUE, charSpacing: 1, isTextBox: true, margin: 0 });
    s.addText("max(P(phish), P(spam)) \u2014 measures raw model confidence in the winning class.", {
        x: 0.85, y: 4.7, w: boxW - 0.5, h: 2.0, fontFace: BODY_FONT, fontSize: 13, color: "D7E1E9", isTextBox: true, margin: 0,
    });

    const x2 = 0.6 + boxW + 0.4;
    s.addShape("roundRect", { x: x2, y: 4.15, w: boxW, h: 2.7, rectRadius: 0.08, fill: { color: "132A3D" }, line: { type: "none" } });
    s.addText("PREDICTION MARGIN", { x: x2 + 0.25, y: 4.35, w: boxW - 0.5, h: 0.3, fontFace: BODY_FONT, bold: true, fontSize: 12, color: RED, charSpacing: 1, isTextBox: true, margin: 0 });
    s.addText('|P(phish) \u2212 P(spam)| \u2014 a split prediction (55% vs 45%) has a tiny margin (0.10), severely penalizing trust and forcing human review.', {
        x: x2 + 0.25, y: 4.7, w: boxW - 0.5, h: 2.0, fontFace: BODY_FONT, fontSize: 13, color: "D7E1E9", isTextBox: true, margin: 0,
    });
    footer(s, 12, true);
}

// =====================================================================
// SLIDE 13 — 4-TIER ROUTING + SECURITY OVERRIDE
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 6 · Operational Routing");
    title(s, "Four-Tier Routing Spectrum");

    const bands = [
        ["Band 1", "\u2265 90%", "Autonomous\nTriage", "Auto-suppress spam / auto-block phishing. Covers 98.8% of daily queue.", STEEL],
        ["Band 2", "75\u201390%", "Auto + Audit\nFlag", "Automated routing with passive audit logging for QA sampling.", "3E7CA6"],
        ["Band 3", "55\u201375%", "Analyst\nReview", "Deferred to Tier-2 queue with full TreeSHAP evidence.", BLUE],
        ["Band 4", "< 55%", "Priority\nEscalation", "Immediate top-of-queue manual triage for conflicting signals.", RED],
    ];
    const bw = 2.9, bh = 3.1, bx0 = 0.6, by = 1.55, bgap = 0.15;
    bands.forEach((b, i) => {
        const x = bx0 + i * (bw + bgap);
        s.addShape("roundRect", { x, y: by, w: bw, h: bh, rectRadius: 0.08, fill: { color: b[4] }, line: { type: "none" } });
        s.addText(b[0], { x: x + 0.2, y: by + 0.18, w: bw - 0.4, h: 0.3, fontFace: BODY_FONT, bold: true, fontSize: 11, color: "FFFFFF", charSpacing: 1, isTextBox: true, margin: 0 });
        s.addText(b[1], { x: x + 0.2, y: by + 0.48, w: bw - 0.4, h: 0.55, fontFace: TITLE_FONT, bold: true, fontSize: 24, color: "FFFFFF", isTextBox: true, margin: 0 });
        s.addText(b[2], { x: x + 0.2, y: by + 1.05, w: bw - 0.4, h: 0.65, fontFace: BODY_FONT, bold: true, fontSize: 13, color: "FFFFFF", isTextBox: true, margin: 0 });
        s.addText(b[3], { x: x + 0.2, y: by + 1.75, w: bw - 0.4, h: 1.2, fontFace: BODY_FONT, fontSize: 10, color: "F0F4F7", isTextBox: true, margin: 0 });
    });

    // Security override strip
    s.addShape("roundRect", { x: 0.6, y: 4.95, w: 12.1, h: 1.85, rectRadius: 0.08, fill: { color: NAVY }, line: { type: "none" } });
    s.addText("ZERO-TOLERANCE SECURITY OVERRIDE", { x: 0.9, y: 5.15, w: 6, h: 0.3, fontFace: BODY_FONT, bold: true, fontSize: 12, color: RED, charSpacing: 1, isTextBox: true, margin: 0 });
    s.addText("Even at a low trust score, dangerous indicator combinations bypass the review queue entirely and escalate directly to quarantine — ensuring high-weight weaponized attacks are never trapped behind review delays.", {
        x: 0.9, y: 5.5, w: 6.2, h: 1.15, fontFace: BODY_FONT, fontSize: 11.5, color: "D7E1E9", isTextBox: true, margin: 0,
    });
    s.addShape("roundRect", { x: 7.4, y: 5.2, w: 5.05, h: 1.45, rectRadius: 0.06, fill: { color: "132A3D" }, line: { color: RED, width: 1 } });
    s.addText("IF P(Phishing) > 0.70 AND (IP URL OR Typosquatting OR Executable/Macro)\n\u21D2 IMMEDIATE QUARANTINE", {
        x: 7.6, y: 5.2, w: 4.65, h: 1.45, fontFace: "Courier New", bold: true, fontSize: 11, color: "FFD166", align: "center", valign: "middle", isTextBox: true, margin: 0,
    });
    footer(s, 13, false);
}

// =====================================================================
// SLIDE 14 — OPERATIONAL PLATFORM, 4 PILLARS
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 7 · The SOC Platform");
    title(s, "An Analyst-Centric Operational Platform");

    const pillars = [
        ["Automated Inbound Triage", "Drag-and-drop RFC-822 MIME parser, sub-15ms classification, trust score assignment, dual-engine toggle (LightGBM vs. RoBERTa)."],
        ["Analyst Review Console", "Dedicated Tier-2 workspace for the 1.2% borderline cases with side-by-side header inspection and one-click override."],
        ["Explainability & Audit Ledger", "Plain-language threat justifications, per-ticket TreeSHAP contributions, full CSV/JSON audit reporting."],
        ["Continuous Supervision", "Rolling 7-day volume tracking, auto-alerting past 20% override rate, hot model promotion with zero downtime."],
    ];
    const cw = 5.85, ch = 2.35, gx = 0.4, gy = 0.3, ox = 0.6, oy = 1.55;
    pillars.forEach((p, i) => {
        const col = i % 2, row = Math.floor(i / 2);
        const x = ox + col * (cw + gx), y = oy + row * (ch + gy);
        s.addShape("roundRect", { x, y, w: cw, h: ch, rectRadius: 0.08, fill: { color: i % 2 === row % 2 ? NAVY : STEEL }, line: { type: "none" } });
        circleNum(s, x + 0.3, y + 0.3, 0.55, i + 1, "FFFFFF", i % 2 === row % 2 ? NAVY : STEEL, 18);
        s.addText(p[0], { x: x + 1.05, y: y + 0.28, w: cw - 1.3, h: 0.6, fontFace: BODY_FONT, bold: true, fontSize: 15, color: WHITE, valign: "middle", isTextBox: true, margin: 0 });
        s.addText(p[1], { x: x + 0.3, y: y + 1.0, w: cw - 0.6, h: 1.25, fontFace: BODY_FONT, fontSize: 11.5, color: "D7E1E9", isTextBox: true, margin: 0 });
    });
    footer(s, 14, false);
}

// =====================================================================
// SLIDE 15 — CLOSED-LOOP FEEDBACK CYCLE
// =====================================================================
{
    const s = bgSlide(false);
    kicker(s, "Module 7 · Closed-Loop Learning");
    title(s, "The Organic Solution to Data Scarcity");

    const steps = [
        ["Ambiguous\nDeferral", "Borderline emails (<75% trust) route to Tier-2 review."],
        ["Analyst Ground\nTruth", "Analysts inspect evidence and record expert verdicts."],
        ["Hard-Example\nLedger", "Full context and feature vectors stored in ground truth store."],
        ["Drift\nMonitoring", "Rolling agreement tracked; alerts past 20% override rate."],
        ["Continuous\nRetraining", "Studio fine-tunes on accumulated hard edge cases with validation gates."],
        ["Hot\nPromotion", "Champion checkpoint reloads into active memory, zero downtime."],
    ];
    const positions = [
        [0.6, 1.7], [4.75, 1.7], [8.9, 1.7],
        [8.9, 4.75], [4.75, 4.75], [0.6, 4.75],
    ];
    const cw = 3.75, ch = 1.85;
    steps.forEach((st, i) => {
        const [x, y] = positions[i];
        s.addShape("roundRect", {
            x, y, w: cw, h: ch, rectRadius: 0.08, fill: { color: CARDBG }, line: { color: LINE, width: 1 },
            shadow: { type: "outer", color: "9AA7B4", opacity: 0.2, blur: 6, offset: 2, angle: 90 }
        });
        circleNum(s, x + 0.2, y + 0.2, 0.5, i + 1, i % 2 === 0 ? STEEL : RED, WHITE, 15);
        s.addText(st[0], { x: x + 0.85, y: y + 0.14, w: cw - 1.05, h: 0.65, fontFace: BODY_FONT, bold: true, fontSize: 12.5, color: NAVY, isTextBox: true, margin: 0 });
        s.addText(st[1], { x: x + 0.2, y: y + 0.85, w: cw - 0.4, h: 0.95, fontFace: BODY_FONT, fontSize: 10, color: MUTED, isTextBox: true, margin: 0 });
    });

    // connecting arrows (simple chevrons) top row and bottom row + verticals
    const topCenterY = 1.7 + ch / 2, botCenterY = 4.75 + ch / 2, midGapY = (1.7 + ch + 4.75) / 2;
    s.addShape("rightArrow", { x: 4.375, y: topCenterY - 0.11, w: 0.35, h: 0.22, fill: { color: MUTED }, line: { type: "none" } });
    s.addShape("rightArrow", { x: 8.525, y: topCenterY - 0.11, w: 0.35, h: 0.22, fill: { color: MUTED }, line: { type: "none" } });
    s.addShape("downArrow", { x: 10.6, y: midGapY - 0.175, w: 0.22, h: 0.35, fill: { color: MUTED }, line: { type: "none" } });
    s.addShape("leftArrow", { x: 8.525, y: botCenterY - 0.11, w: 0.35, h: 0.22, fill: { color: MUTED }, line: { type: "none" } });
    s.addShape("leftArrow", { x: 4.375, y: botCenterY - 0.11, w: 0.35, h: 0.22, fill: { color: MUTED }, line: { type: "none" } });
    s.addShape("upArrow", { x: 2.35, y: midGapY - 0.175, w: 0.22, h: 0.35, fill: { color: MUTED }, line: { type: "none" } });

    s.addText("Instead of waiting for public datasets, daily operations organically collect the ambiguous edge cases needed to scale training past 100k+ samples.", {
        x: 0.6, y: 6.75, w: 12.1, h: 0.4, fontFace: BODY_FONT, italic: true, fontSize: 11, color: MUTED, align: "center", isTextBox: true, margin: 0,
    });
    footer(s, 15, false);
}

// =====================================================================
// SLIDE 16 — ROADMAP + CLOSING SUMMARY
// =====================================================================
{
    const s = bgSlide(true);
    kicker(s, "Roadmap & Summary", BLUE);
    title(s, "Continuous Improvement, Not a Finish Line", { color: WHITE });

    pillHeader(s, 0.6, 1.55, 5.9, "THE PATH FORWARD", STEEL);
    bulletBlock(s, 0.6, 2.15, 5.9, 2.15, [
        "Connect gateway report-phish webhooks (Proofpoint/Defender) to inbound triage; route high-priority alerts straight to SOC ticketing (ServiceNow/Jira).",
        "Recalibrate on schedule: once ~5,000 analyst verdicts accumulate on borderline tickets, run calibration retraining to resolve ECE on real operational edge cases.",
        "Fine-tune continuously: as the ground-truth store passes 100k+ samples, fine-tune RoBERTa on accumulated hard examples rather than the original public corpus.",
        "Activate two-stage routing: LightGBM handles fast first-pass triage; fine-tuned RoBERTa takes over for deep contextual disambiguation on ambiguous BEC pretexts.",
    ], { fontSize: 11, color: "D7E1E9", spaceAfter: 10 });

    pillHeader(s, 6.8, 1.55, 5.9, "WHY ROBERTA IS THE EVENTUAL CHAMPION", RED);
    bulletBlock(s, 6.8, 2.15, 5.9, 2.15, [
        "Its 125M parameters were data-starved at just 15,483 training emails — the ceiling was sample volume, not architecture.",
        "Tree-based features plateau once explicit structural signals (URLs, headers, attachments) are exhausted; transformer attention keeps improving with more context.",
        "The closed-loop feedback store is built to deliver exactly the volume of real, conversational BEC edge cases RoBERTa needs to overtake LightGBM.",
    ], { fontSize: 11, color: "D7E1E9", spaceAfter: 10 });

    s.addShape("line", { x: 0.6, y: 4.35, w: 12.1, h: 0, line: { color: "2C4157", width: 1 } });

    const metrics = [["98.01%", "Phishing Recall"], ["97.62%", "Accuracy"], ["0.9845", "ROC-AUC"], ["11.8 ms", "P95 Latency"], ["98.8%", "Autonomous"]];
    const mw = 2.3, mgap = 0.2, mx = 0.6, my = 4.75;
    metrics.forEach((m, i) => {
        const x = mx + i * (mw + mgap);
        s.addText(m[0], { x, y: my, w: mw, h: 0.55, fontFace: TITLE_FONT, bold: true, fontSize: 22, color: WHITE, align: "center", isTextBox: true, margin: 0 });
        s.addText(m[1], { x, y: my + 0.55, w: mw, h: 0.35, fontFace: BODY_FONT, fontSize: 10, color: "9FB2C4", align: "center", isTextBox: true, margin: 0 });
    });

    s.addText("Intelligent Email Triage turns SOC noise into signal — precision automation where it's safe, human judgment where it matters.", {
        x: 0.6, y: 5.9, w: 12.1, h: 0.7, fontFace: TITLE_FONT, italic: true, fontSize: 16, color: WHITE, align: "center", isTextBox: true, margin: 0,
    });
    footer(s, 16, true);
}

pres.writeFile({ fileName: "final.pptx" }).then(() => {
    console.log("Deck written.");
});