"""
Phase 5 — Assemble Phishing Class (~20k)

Organic: 1,415 Nazario samples
Gap: ~18,585 samples needed via augmentation

Augmentation strategy:
1. Text perturbation of real samples (synonym swap, sender/brand variation)
   → inherit source metadata
2. Template-generated samples per subtype
   → explicit metadata: spf=fail, dkim=fail, domain_age=1-30 days, first_time_domain=True

Subtype targets (each ≥ 10% = 2,000 samples):
  1. credential_harvesting   → 4,000
  2. bec                     → 4,000  (all 5 sub-patterns, ~800 each)
  3. malware_delivery        → 3,000
  4. invoice_payment_fraud   → 3,000
  5. redirect_landing_page   → 6,000  (fill remainder)

BEC sub-patterns (~800 each):
  - wire_transfer
  - gift_card
  - invoice_change
  - bank_account_change
  - payroll_redirect
"""

import json
import random
import re
import copy
from pathlib import Path
from collections import defaultdict

random.seed(42)

BASE   = Path(__file__).parent / "data"
INPUT  = BASE / "parsed/phishing_deduped.jsonl"
OUTPUT = BASE / "parsed/phishing_class.jsonl"

TARGET = 20_000

# ---------------------------------------------------------------------------
# Template data
# ---------------------------------------------------------------------------

BRANDS = [
    "PayPal", "Amazon", "Microsoft", "Apple", "Google", "Chase", "Wells Fargo",
    "Bank of America", "Netflix", "Dropbox", "DocuSign", "LinkedIn", "Facebook",
    "Instagram", "Twitter", "Outlook", "OneDrive", "Adobe", "Zoom", "Slack",
]

EXEC_NAMES = [
    "James Wilson", "Sarah Mitchell", "Robert Chen", "Emily Davis", "Michael Brown",
    "Jennifer Taylor", "David Anderson", "Lisa Thompson", "Christopher Martinez",
    "Amanda Johnson", "Daniel White", "Jessica Harris", "Matthew Clark",
    "Ashley Lewis", "Andrew Robinson", "Stephanie Walker", "Ryan Hall",
    "Nicole Young", "Kevin Allen", "Megan Scott",
]

COMPANY_NAMES = [
    "Apex Solutions", "Meridian Group", "Pinnacle Corp", "Summit Enterprises",
    "Horizon Technologies", "Nexus Partners", "Vanguard Industries",
    "Catalyst Systems", "Synergy Global", "Vertex Holdings",
    "Quantum Dynamics", "Stellar Networks", "Fusion Capital",
    "Paradigm Consulting", "Momentum Ventures",
]

AMOUNTS = [
    "$12,500", "$24,750", "$8,200", "$45,000", "$3,800", "$67,500",
    "$15,000", "$32,000", "$9,500", "$125,000", "$7,250", "$18,900",
    "$55,000", "$4,600", "$28,000",
]

URGENCY_PHRASES = [
    "This is time-sensitive.",
    "Please handle this immediately.",
    "I need this done today.",
    "This is urgent — please respond ASAP.",
    "Do not delay on this.",
    "I'm in a meeting and need this resolved now.",
    "Please prioritize this request.",
    "This must be completed before end of business.",
]

CREDENTIAL_SUBJECTS = [
    "Your {brand} account has been suspended",
    "Action required: Verify your {brand} account",
    "Unusual sign-in activity on your {brand} account",
    "Your {brand} password will expire soon",
    "Confirm your {brand} email address",
    "Security alert: {brand} account access",
    "Your {brand} account needs attention",
    "Important: Update your {brand} billing information",
    "Your {brand} account has been locked",
    "Verify your identity to continue using {brand}",
]

CREDENTIAL_BODIES = [
    """Dear {brand} Customer,

We have detected unusual activity on your account. To protect your security, we have temporarily limited access to your account.

To restore full access, please verify your identity by clicking the link below:

{url}

If you do not verify within 24 hours, your account will be permanently suspended.

{brand} Security Team""",

    """Hello,

Your {brand} account password is about to expire. To keep your account secure and avoid interruption of service, please update your password immediately.

Click here to update your password: {url}

This link will expire in 12 hours.

Thank you,
{brand} Account Services""",

    """IMPORTANT NOTICE

We noticed a sign-in attempt to your {brand} account from an unrecognized device.

Location: {location}
Device: {device}
Time: {time}

If this was you, no action is needed. If this was NOT you, secure your account immediately:

{url}

{brand} Trust & Safety""",
]

MALWARE_SUBJECTS = [
    "Invoice #{inv} attached",
    "Your order confirmation - {brand}",
    "Document shared with you: {doc}",
    "Please review and sign: {doc}",
    "Fax received from {number}",
    "Voicemail from {number}",
    "Shipping notification - Track your package",
    "Your tax document is ready",
    "Payroll report Q{q} attached",
    "Contract for review: {doc}",
]

MALWARE_BODIES = [
    """Please find attached the invoice for services rendered.

Invoice Number: {inv}
Amount Due: {amount}
Due Date: {date}

Please open the attached document to review the details and process payment.

If you have any questions, please contact our billing department.

Best regards,
Accounts Receivable""",

    """You have received a secure document from {sender}.

Document: {doc}
Shared on: {date}

To view this document, please download and open the attachment. You may need to enable macros to view the full content.

This document will expire in 48 hours.

DocuShare Secure""",

    """A voicemail message has been left for you.

From: {number}
Duration: {duration}
Received: {date}

Please open the attached audio file to listen to your message.

Voicemail Service""",
]

INVOICE_SUBJECTS = [
    "Urgent: Wire transfer required - {amount}",
    "Payment request - Invoice #{inv}",
    "Vendor payment update required",
    "Change of bank account details",
    "Outstanding invoice - immediate payment needed",
    "Payment confirmation needed: {amount}",
    "Updated banking information for {company}",
    "Re: Invoice #{inv} - payment instructions",
]

INVOICE_BODIES = [
    """Hi,

I hope this email finds you well. We need to process a payment of {amount} to our vendor {company} today.

Please initiate the wire transfer to the following account:

Bank: {bank}
Account Name: {company}
Account Number: {acct}
Routing Number: {routing}
Reference: INV-{inv}

Please confirm once the transfer has been initiated.

Thank you,
{sender}""",

    """Dear Accounts Payable,

Please be advised that our banking details have changed effective immediately. All future payments should be directed to our new account:

New Bank: {bank}
Account: {acct}
Sort Code: {routing}

Please update your records and process the outstanding invoice #{inv} for {amount} to the new account.

Regards,
{company} Finance Team""",
]

BEC_TEMPLATES = {
    "wire_transfer": {
        "subjects": [
            "Urgent wire transfer needed",
            "Confidential - wire transfer request",
            "Time sensitive: wire transfer {amount}",
            "Need wire transfer processed today",
            "Immediate wire transfer - {amount}",
        ],
        "bodies": [
            """Hi,

I need you to process a wire transfer of {amount} today. This is for a confidential acquisition we are finalizing.

Please send to:
Bank: {bank}
Account: {acct}
Routing: {routing}

Do not discuss this with anyone else in the office. I will explain everything once the deal closes.

{exec_name}
{title}""",
            """I'm currently in a meeting and cannot take calls. I need a wire transfer of {amount} sent out before 3pm today.

Beneficiary: {company}
Bank: {bank}
Account Number: {acct}
Routing: {routing}

{urgency}

{exec_name}""",
        ],
    },
    "gift_card": {
        "subjects": [
            "Quick favor needed",
            "Can you help me with something?",
            "Urgent request - gift cards",
            "Need your help - confidential",
            "Are you available?",
        ],
        "bodies": [
            """Hi,

I need a quick favor. Can you purchase {n} x {brand} gift cards worth {amount} each? I need them for a client appreciation event today.

Please scratch off the back and send me the redemption codes by email. I'll reimburse you right away.

{urgency}

{exec_name}""",
            """Are you available? I need you to pick up some gift cards for me. I'm in back-to-back meetings all day.

Get {n} Google Play gift cards, {amount} each. Send me the card numbers and PINs when you have them.

Keep this between us for now — it's a surprise for the team.

Thanks,
{exec_name}""",
        ],
    },
    "invoice_change": {
        "subjects": [
            "Updated payment instructions for invoice #{inv}",
            "Change to invoice #{inv} - please read",
            "Important: revised banking details",
            "Invoice #{inv} - new payment account",
            "Please update payment details for {company}",
        ],
        "bodies": [
            """Hi,

Please note that our banking details have changed. For invoice #{inv} ({amount}), please use the following new account:

Bank: {bank}
Account: {acct}
Routing: {routing}

Please do not use the old account details. {urgency}

{exec_name}
{company}""",
        ],
    },
    "bank_account_change": {
        "subjects": [
            "Vendor bank account update - {company}",
            "New banking details for {company}",
            "Important: {company} payment information change",
            "Please update {company} account details",
        ],
        "bodies": [
            """Dear {recipient},

We are writing to inform you that {company} has changed its banking details. Please update your records immediately.

Old Account: ending in {old_acct}
New Account: {acct}
Bank: {bank}
Routing: {routing}

Please ensure all future payments and any pending invoices are directed to the new account. {urgency}

{company} Finance""",
        ],
    },
    "payroll_redirect": {
        "subjects": [
            "Payroll direct deposit change request",
            "Update my direct deposit information",
            "Payroll bank account change",
            "Please update my payment details",
            "Direct deposit update - urgent",
        ],
        "bodies": [
            """Hi HR,

I need to update my direct deposit information effective this pay period. Please change my bank account to:

Bank: {bank}
Account Number: {acct}
Routing Number: {routing}
Account Type: Checking

{urgency}

Please confirm once updated.

{exec_name}""",
        ],
    },
}

REDIRECT_SUBJECTS = [
    "You have a pending notification",
    "Your account statement is ready",
    "Click here to claim your reward",
    "You've been selected for a special offer",
    "Your package could not be delivered",
    "Action required: complete your profile",
    "Exclusive offer for you",
    "Your subscription is expiring",
    "Confirm your recent transaction",
    "You have a new message",
]

REDIRECT_BODIES = [
    """Hello,

You have a pending notification that requires your attention.

Click the link below to view your notification:

{url}

This link will expire in 24 hours.

Customer Service""",

    """Congratulations! You have been selected to receive a special reward.

To claim your reward, please visit:

{url}

Offer expires soon. Act now!""",

    """We were unable to deliver your package.

To reschedule delivery, please confirm your address at:

{url}

Your package will be returned to sender if not claimed within 48 hours.

Delivery Service""",
]

PHISHING_URLS = [
    "http://secure-{brand}-login.{tld}/verify",
    "http://{brand}.account-verify.{tld}/signin",
    "http://update-{brand}.{tld}/confirm",
    "http://{brand}-security.{tld}/alert",
    "http://login.{brand}-support.{tld}/",
    "http://{brand}.{tld}.attacker.net/login",
    "http://192.168.{a}.{b}/phish",
    "http://bit.ly/{code}",
    "http://tinyurl.com/{code}",
    "http://{brand}-verify.xyz/account",
]

PHISHING_TLDS = ["xyz", "top", "tk", "ml", "click", "online", "site", "info"]

LOCATIONS = ["Moscow, Russia", "Beijing, China", "Lagos, Nigeria", "Unknown location",
             "Bucharest, Romania", "Kyiv, Ukraine"]
DEVICES = ["Windows PC", "Android device", "Unknown device", "Linux machine"]
TIMES = ["2:34 AM", "3:17 AM", "11:52 PM", "4:08 AM"]
BANKS = ["First National Bank", "Pacific Trust", "Metro Financial", "Coastal Credit Union",
         "Heritage Bank", "Summit Financial", "Apex Banking"]
TITLES = ["CEO", "CFO", "COO", "President", "Managing Director", "VP Finance"]
DURATIONS = ["0:32", "1:14", "0:47", "2:03", "0:58"]
NUMBERS = ["+1-555-0{:03d}".format(i) for i in range(100, 200)]


def rand_url(brand=""):
    brand_slug = brand.lower().replace(" ", "") if brand else random.choice([b.lower() for b in BRANDS])
    tld = random.choice(PHISHING_TLDS)
    template = random.choice(PHISHING_URLS)
    code = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
    a, b = random.randint(0, 255), random.randint(0, 255)
    return template.format(brand=brand_slug, tld=tld, code=code, a=a, b=b)


def rand_acct():
    return "".join(str(random.randint(0, 9)) for _ in range(10))


def rand_routing():
    return "".join(str(random.randint(0, 9)) for _ in range(9))


def rand_inv():
    return str(random.randint(10000, 99999))


def phishing_meta(subtype):
    """Return explicit metadata for a template-generated phishing sample."""
    return {
        "source": "augmented_template",
        "label": "phishing",
        "spf_result": random.choice(["fail", "fail", "softfail", "none"]),
        "dkim_result": random.choice(["fail", "fail", "none"]),
        "dmarc_result": random.choice(["fail", "none"]),
        "attachment_count": 1 if subtype == "malware_delivery" else 0,
        "reply_to_mismatch": random.random() < 0.6,
        "html_text_ratio": round(random.uniform(0.3, 2.5), 2),
        "augmented": True,
        "domain_age_reliable": False,
        "era_bucket": random.choice(["mid", "recent"]),
        "subtype": subtype,
        "sender_domain_age_days": random.randint(1, 30),
        "first_time_domain": True,
    }


def make_credential(n):
    samples = []
    for _ in range(n):
        brand = random.choice(BRANDS)
        subj_tmpl = random.choice(CREDENTIAL_SUBJECTS)
        body_tmpl = random.choice(CREDENTIAL_BODIES)
        url = rand_url(brand)
        subject = subj_tmpl.format(brand=brand)
        body = body_tmpl.format(
            brand=brand, url=url,
            location=random.choice(LOCATIONS),
            device=random.choice(DEVICES),
            time=random.choice(TIMES),
        )
        meta = phishing_meta("credential_harvesting")
        meta.update({
            "subject": subject,
            "body_text": body,
            "sender_display_name": f"{brand} Security <noreply@{brand.lower().replace(' ', '')}-secure.{random.choice(PHISHING_TLDS)}>",
            "headers": {"date": "", "reply_to": "", "received_spf": meta["spf_result"],
                        "authentication_results": "", "sending_ip": ""},
            "urls": [url],
            "url_count": 1,
            "attachments": [{"count": 0, "mime_type": "", "filename": ""}],
        })
        samples.append(meta)
    return samples


def make_malware(n):
    samples = []
    for _ in range(n):
        brand = random.choice(BRANDS)
        subj_tmpl = random.choice(MALWARE_SUBJECTS)
        body_tmpl = random.choice(MALWARE_BODIES)
        inv = rand_inv()
        doc = f"Invoice_{inv}.doc"
        q = random.randint(1, 4)
        number = random.choice(NUMBERS)
        subject = subj_tmpl.format(brand=brand, inv=inv, doc=doc, number=number, q=q)
        body = body_tmpl.format(
            inv=inv, amount=random.choice(AMOUNTS),
            date=f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            sender=random.choice(EXEC_NAMES),
            doc=doc, number=number,
            duration=random.choice(DURATIONS),
        )
        meta = phishing_meta("malware_delivery")
        meta.update({
            "subject": subject,
            "body_text": body,
            "sender_display_name": f"{random.choice(EXEC_NAMES)} <{random.choice(EXEC_NAMES).lower().replace(' ', '.')}@{random.choice(COMPANY_NAMES).lower().replace(' ', '')}.{random.choice(PHISHING_TLDS)}>",
            "headers": {"date": "", "reply_to": "", "received_spf": meta["spf_result"],
                        "authentication_results": "", "sending_ip": ""},
            "urls": [],
            "url_count": 0,
            "attachments": [{"count": 1, "mime_type": "application/msword", "filename": doc}],
        })
        samples.append(meta)
    return samples


def make_invoice(n):
    samples = []
    for _ in range(n):
        company = random.choice(COMPANY_NAMES)
        exec_name = random.choice(EXEC_NAMES)
        inv = rand_inv()
        amount = random.choice(AMOUNTS)
        bank = random.choice(BANKS)
        acct = rand_acct()
        routing = rand_routing()
        subj_tmpl = random.choice(INVOICE_SUBJECTS)
        body_tmpl = random.choice(INVOICE_BODIES)
        subject = subj_tmpl.format(inv=inv, amount=amount, company=company)
        body = body_tmpl.format(
            inv=inv, amount=amount, company=company,
            bank=bank, acct=acct, routing=routing,
            sender=exec_name,
        )
        meta = phishing_meta("invoice_payment_fraud")
        meta.update({
            "subject": subject,
            "body_text": body,
            "sender_display_name": f"{exec_name} <{exec_name.lower().replace(' ', '.')}@{company.lower().replace(' ', '')}.{random.choice(PHISHING_TLDS)}>",
            "headers": {"date": "", "reply_to": "", "received_spf": meta["spf_result"],
                        "authentication_results": "", "sending_ip": ""},
            "urls": [],
            "url_count": 0,
            "attachments": [{"count": 0, "mime_type": "", "filename": ""}],
        })
        samples.append(meta)
    return samples


def make_bec(n_per_pattern):
    samples = []
    for pattern, templates in BEC_TEMPLATES.items():
        for _ in range(n_per_pattern):
            exec_name = random.choice(EXEC_NAMES)
            company = random.choice(COMPANY_NAMES)
            amount = random.choice(AMOUNTS)
            bank = random.choice(BANKS)
            acct = rand_acct()
            routing = rand_routing()
            inv = rand_inv()
            brand = random.choice(BRANDS)
            n_cards = random.randint(5, 20)
            card_amount = random.choice(["$100", "$200", "$50", "$500"])
            urgency = random.choice(URGENCY_PHRASES)
            title = random.choice(TITLES)
            recipient = random.choice(EXEC_NAMES)
            old_acct = rand_acct()[-4:]

            subj = random.choice(templates["subjects"]).format(
                amount=amount, inv=inv, company=company, brand=brand,
            )
            body = random.choice(templates["bodies"]).format(
                exec_name=exec_name, company=company, amount=amount,
                bank=bank, acct=acct, routing=routing, inv=inv,
                brand=brand, n=n_cards, urgency=urgency, title=title,
                recipient=recipient, old_acct=old_acct,
            )
            meta = phishing_meta("bec")
            meta["bec_subpattern"] = pattern
            meta.update({
                "subject": subj,
                "body_text": body,
                "sender_display_name": f"{exec_name} <{exec_name.lower().replace(' ', '.')}@{company.lower().replace(' ', '')}.{random.choice(PHISHING_TLDS)}>",
                "headers": {"date": "", "reply_to": exec_name.lower().replace(' ', '.') + "@gmail.com",
                            "received_spf": meta["spf_result"],
                            "authentication_results": "", "sending_ip": ""},
                "urls": [],
                "url_count": 0,
                "attachments": [{"count": 0, "mime_type": "", "filename": ""}],
                "reply_to_mismatch": True,  # BEC hallmark
            })
            samples.append(meta)
    return samples


def make_redirect(n):
    samples = []
    for _ in range(n):
        url = rand_url()
        subject = random.choice(REDIRECT_SUBJECTS)
        body = random.choice(REDIRECT_BODIES).format(url=url)
        meta = phishing_meta("redirect_landing_page")
        meta.update({
            "subject": subject,
            "body_text": body,
            "sender_display_name": f"Notification <noreply@{random.choice(PHISHING_TLDS)}.{random.choice(PHISHING_TLDS)}>",
            "headers": {"date": "", "reply_to": "", "received_spf": meta["spf_result"],
                        "authentication_results": "", "sending_ip": ""},
            "urls": [url],
            "url_count": 1,
            "attachments": [{"count": 0, "mime_type": "", "filename": ""}],
        })
        samples.append(meta)
    return samples


def perturb(record, idx):
    """Light text perturbation of a real sample — inherit source metadata."""
    r = copy.deepcopy(record)
    r["augmented"] = True
    r["source"] = record.get("source", "nazario") + "_perturbed"
    r["subtype"] = record.get("subtype", "credential_harvesting")
    r["era_bucket"] = record.get("era_bucket", "legacy")

    # Vary subject slightly
    subj = r.get("subject", "")
    variations = [
        subj,
        "Re: " + subj,
        "Fwd: " + subj,
        subj + " - Action Required",
        subj.replace("your", "Your").replace("Your", "your"),
    ]
    r["subject"] = random.choice(variations)
    return r


def main():
    # Load organic phishing
    organic = []
    with open(INPUT) as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                r["era_bucket"] = "legacy"
                r["subtype"] = "credential_harvesting"  # Nazario is mostly credential/generic
                r["augmented"] = False
                organic.append(r)

    print(f"Organic phishing: {len(organic)}")

    # Perturbation augmentation of organic samples (up to 2x)
    perturbed = [perturb(r, i) for i, r in enumerate(organic * 2)]
    random.shuffle(perturbed)
    perturbed = perturbed[:2_000]  # cap at 2k perturbed

    # Template generation per subtype
    credential = make_credential(4_000)
    malware    = make_malware(3_000)
    invoice    = make_invoice(3_000)
    bec        = make_bec(800)   # 800 per pattern × 5 patterns = 4,000
    redirect   = make_redirect(6_000)

    all_samples = organic + perturbed + credential + malware + invoice + bec + redirect
    random.shuffle(all_samples)

    # Trim to target
    if len(all_samples) > TARGET:
        all_samples = all_samples[:TARGET]

    print(f"Total phishing class: {len(all_samples)}")

    from collections import Counter
    subtypes = Counter(r.get("subtype", "unknown") for r in all_samples)
    print("Subtype breakdown:", dict(subtypes))
    augmented = Counter(r.get("augmented", False) for r in all_samples)
    print("Augmented:", dict(augmented))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as out:
        for r in all_samples:
            out.write(json.dumps(r) + "\n")
    print(f"Written: {OUTPUT}")


if __name__ == "__main__":
    main()
