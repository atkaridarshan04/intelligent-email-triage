"""
generate_synthetic.py — Track B synthetic sample generation.

Produces JSON files consumed by parse_json() in email_parser.py.
Output: data/raw/synthetic/phishing/*.json
        data/raw/synthetic/spam/*.json

Subtypes generated (phishing):
  - credential_harvesting  : 1200 samples
  - bec_wire_transfer      :  250 samples  ┐
  - bec_gift_card          :  250 samples  │ BEC sub-patterns
  - bec_invoice_change     :  250 samples  │
  - bec_bank_account       :  250 samples  │
  - bec_payroll_redirect   :  250 samples  ┘
  - invoice_fraud          :  800 samples
  - malware_delivery       :  700 samples
  - redirect_phishing      :  700 samples

Spam generated:
  - synthetic_spam (recent) : 800 samples

All synthetic samples:
  - era_bucket = "recent"
  - augmented  = True
  - structured features explicitly assigned (not inherited)
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from src.utils.io import email_id

random.seed(42)

OUT_PHISH = Path("data/raw/synthetic/phishing")
OUT_SPAM  = Path("data/raw/synthetic/spam")
OUT_PHISH.mkdir(parents=True, exist_ok=True)
OUT_SPAM.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Shared vocabulary pools
# ---------------------------------------------------------------------------

BRANDS = [
    "Microsoft", "PayPal", "Amazon", "Apple", "Google", "Netflix", "Chase",
    "Wells Fargo", "Bank of America", "Dropbox", "LinkedIn", "DocuSign",
    "Adobe", "Salesforce", "Okta", "Zoom", "Office 365", "OneDrive",
    "Intuit", "QuickBooks",
]
BRAND_DOMAINS = [
    "microsoft.com", "paypal.com", "amazon.com", "apple.com", "google.com",
    "netflix.com", "chase.com", "wellsfargo.com", "bankofamerica.com",
    "dropbox.com", "linkedin.com", "docusign.com", "adobe.com",
    "salesforce.com", "okta.com", "zoom.us", "office365.com",
    "onedrive.com", "intuit.com", "quickbooks.intuit.com",
]
ATTACKER_DOMAINS = [
    "secure-login.xyz", "account-verify.top", "signin-portal.click",
    "update-required.ml", "auth-check.tk", "verify-now.ga",
    "account-suspended.cf", "login-secure.pw", "portal-access.icu",
    "user-verify.vip", "secure-account.work", "signin-update.loan",
    "account-alert.win", "verify-identity.download", "auth-portal.stream",
    "secure-verify.online", "login-portal.site", "account-check.biz",
]
FREE_SENDERS = [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com",
]
EXEC_NAMES = [
    "James Wilson", "Sarah Mitchell", "Robert Chen", "David Park",
    "Michael Torres", "Jennifer Adams", "Christopher Lee", "Amanda Foster",
]
EXEC_TITLES = ["CEO", "CFO", "COO", "VP of Finance", "Director of Operations"]
EMPLOYEE_NAMES = [
    "Alex Johnson", "Maria Garcia", "Kevin Smith", "Lisa Brown",
    "Daniel Martinez", "Rachel Thompson", "Brian White", "Emily Davis",
]
COMPANIES = [
    "Acme Corp", "GlobalTech Solutions", "Meridian Enterprises",
    "Apex Industries", "Nexus Group", "Pinnacle Systems",
]
INVOICE_VENDORS = [
    "TechSupply Co", "Office Solutions Ltd", "CloudServices Inc",
    "DataCenter Pro", "Network Systems LLC", "Software Dynamics",
]
MALWARE_SUBJECTS = [
    "Your invoice #{n} is attached",
    "Document requires your signature",
    "Shared file: Q{q} Report.docx",
    "Action required: Review attached contract",
    "Your package delivery notification",
    "Scanned document from printer",
    "Voicemail transcription attached",
    "Fax received — please review",
]
REDIRECT_DOMAINS = [
    "bit.ly", "tinyurl.com", "t.co", "ow.ly", "goo.gl",
    "rb.gy", "cutt.ly", "short.io",
]


def _pick(lst):
    return random.choice(lst)

def _brand_pair():
    i = random.randrange(len(BRANDS))
    return BRANDS[i], BRAND_DOMAINS[i]

def _attacker_url(path="login"):
    return f"https://{_pick(ATTACKER_DOMAINS)}/{path}?token={random.randint(100000,999999)}"

def _redirect_url():
    return f"https://{_pick(REDIRECT_DOMAINS)}/{random.randint(10000,99999)}"

def _n():
    return random.randint(1000, 9999)


# ---------------------------------------------------------------------------
# Phishing generators — each returns a dict matching parse_json schema
# ---------------------------------------------------------------------------

def _credential(i):
    brand, domain = _brand_pair()
    attacker = _pick(ATTACKER_DOMAINS)
    sender_local = random.choice(["security", "noreply", "support", "alert", "verify"])
    url = _attacker_url("verify")
    subjects = [
        f"Action Required: Verify your {brand} account",
        f"Your {brand} account has been suspended",
        f"Unusual sign-in activity detected on your {brand} account",
        f"Confirm your {brand} identity to restore access",
        f"Security alert: {brand} account requires verification",
        f"[{brand}] Please update your password immediately",
    ]
    bodies = [
        f"Dear Customer,\n\nWe detected unusual activity on your {brand} account. "
        f"To secure your account, please verify your identity within 24 hours.\n\n"
        f"Click here to verify: {url}\n\n"
        f"If you do not verify, your account will be suspended.\n\nThe {brand} Security Team",

        f"Hello,\n\nYour {brand} account has been temporarily suspended due to a failed security check. "
        f"Please confirm your credentials to restore access.\n\n"
        f"Verify now: {url}\n\n"
        f"This link expires in 12 hours.\n\n{brand} Support",

        f"Important notice from {brand}:\n\nWe have detected a sign-in attempt from an unrecognized device. "
        f"If this was not you, please secure your account immediately.\n\n"
        f"Secure your account: {url}\n\n"
        f"Regards,\n{brand} Account Security",
    ]
    return {
        "subject": _pick(subjects),
        "body_text": _pick(bodies),
        "sender_display_name": f"{brand} Security",
        "sender_address": f"{sender_local}@{attacker}",
        "reply_to": f"noreply@{_pick(FREE_SENDERS)}",
        "urls": [url],
        "label": "phishing",
        "source": "synthetic",
        "era_bucket": "recent",
        "subtype": "credential_harvesting",
        "augmented": True,
        "display_from_mismatch": True,
        "reply_to_mismatch": True,
        "free_email_sender": False,
        "url_count": 1,
        "domain_count": 1,
        "shortened_url_present": False,
        "suspicious_tld_present": True,
        "ip_literal_url": False,
        "typosquatting_detected": False,
        "brand_mention": True,
        "sender_brand_mismatch": True,
    }


def _bec(subtype, i):
    exec_name = _pick(EXEC_NAMES)
    exec_title = _pick(EXEC_TITLES)
    employee = _pick(EMPLOYEE_NAMES)
    company = _pick(COMPANIES)
    sender_addr = f"{exec_name.lower().replace(' ','.')}.{random.randint(1,99)}@{_pick(FREE_SENDERS)}"

    if subtype == "bec_wire_transfer":
        amount = random.choice([15000, 25000, 48500, 72000, 95000, 120000])
        subject = random.choice([
            f"Urgent wire transfer needed",
            f"Confidential — wire transfer request",
            f"Time-sensitive payment request",
            f"Wire transfer — please action immediately",
        ])
        body = (
            f"Hi {employee.split()[0]},\n\n"
            f"I need you to process an urgent wire transfer of ${amount:,} today. "
            f"This is time-sensitive and must be completed before close of business.\n\n"
            f"Please send to:\nBank: First National\nAccount: {random.randint(10000000,99999999)}\n"
            f"Routing: {random.randint(100000000,999999999)}\n\n"
            f"Do not discuss this with anyone else. I'll explain when I'm back in the office.\n\n"
            f"Thanks,\n{exec_name}\n{exec_title}, {company}"
        )
    elif subtype == "bec_gift_card":
        amount = random.choice([200, 500, 1000, 2000])
        qty = random.choice([5, 10, 20])
        subject = random.choice([
            f"Quick favor needed",
            f"Can you help me with something?",
            f"Urgent request — gift cards",
            f"Need your help right away",
        ])
        body = (
            f"Hi {employee.split()[0]},\n\n"
            f"I'm in a meeting and need a quick favor. Can you purchase {qty} x ${amount} "
            f"Google Play gift cards from a nearby store? Scratch the back and send me the codes.\n\n"
            f"I'll reimburse you as soon as I'm out. Please keep this between us for now.\n\n"
            f"Thanks,\n{exec_name}"
        )
    elif subtype == "bec_invoice_change":
        vendor = _pick(INVOICE_VENDORS)
        amount = random.choice([8500, 14200, 22000, 35000])
        subject = random.choice([
            f"Updated banking details for {vendor}",
            f"Payment instruction change — {vendor}",
            f"Important: New account details for upcoming payment",
        ])
        body = (
            f"Dear {employee.split()[0]},\n\n"
            f"Please be advised that {vendor} has updated their banking details. "
            f"All future payments should be directed to the new account below.\n\n"
            f"Bank: Metro Business Bank\nAccount Name: {vendor}\n"
            f"Account No: {random.randint(10000000,99999999)}\nSort Code: {random.randint(10,99)}-{random.randint(10,99)}-{random.randint(10,99)}\n\n"
            f"Please update your records and process the pending invoice of ${amount:,} to the new account.\n\n"
            f"Regards,\n{exec_name}\n{exec_title}"
        )
    elif subtype == "bec_bank_account":
        subject = random.choice([
            f"Bank account change notification",
            f"Updated payment details",
            f"New bank account for payroll",
        ])
        body = (
            f"Hi {employee.split()[0]},\n\n"
            f"I've recently changed my bank account. Please update payroll with my new details:\n\n"
            f"Bank: {random.choice(['Chase','Wells Fargo','Bank of America','Citibank'])}\n"
            f"Account: {random.randint(10000000,99999999)}\n"
            f"Routing: {random.randint(100000000,999999999)}\n\n"
            f"Please make sure this takes effect for the next pay cycle.\n\n"
            f"Thanks,\n{exec_name}"
        )
    else:  # bec_payroll_redirect
        subject = random.choice([
            f"Payroll direct deposit update",
            f"Change of bank details — payroll",
            f"Direct deposit change request",
        ])
        body = (
            f"Hello,\n\n"
            f"I would like to update my direct deposit information effective immediately. "
            f"Please redirect my salary to the following account:\n\n"
            f"Routing Number: {random.randint(100000000,999999999)}\n"
            f"Account Number: {random.randint(10000000,99999999)}\nAccount Type: Checking\n\n"
            f"Please confirm once updated.\n\nBest regards,\n{exec_name}"
        )

    return {
        "subject": subject,
        "body_text": body,
        "sender_display_name": exec_name,
        "sender_address": sender_addr,
        "reply_to": sender_addr,
        "urls": [],
        "label": "phishing",
        "source": "synthetic",
        "era_bucket": "recent",
        "subtype": subtype,
        "augmented": True,
        "display_from_mismatch": True,
        "reply_to_mismatch": False,
        "free_email_sender": True,
        "url_count": 0,
        "domain_count": 0,
        "shortened_url_present": False,
        "suspicious_tld_present": False,
        "ip_literal_url": False,
        "typosquatting_detected": False,
        "brand_mention": False,
        "sender_brand_mismatch": False,
    }


def _invoice_fraud(i):
    vendor = _pick(INVOICE_VENDORS)
    amount = random.choice([1200, 3400, 5600, 8900, 12000, 18500, 24000])
    inv_num = _n()
    attacker = _pick(ATTACKER_DOMAINS)
    url = f"https://{attacker}/invoice/{inv_num}"
    subjects = [
        f"Invoice #{inv_num} from {vendor} — payment due",
        f"OVERDUE: Invoice #{inv_num} requires immediate payment",
        f"Final notice: Invoice #{inv_num} — ${amount:,}",
        f"Payment reminder: {vendor} invoice #{inv_num}",
    ]
    body = (
        f"Dear Accounts Payable,\n\n"
        f"Please find attached invoice #{inv_num} for ${amount:,} from {vendor}.\n\n"
        f"Payment is due within 3 business days to avoid late fees.\n\n"
        f"View and pay invoice: {url}\n\n"
        f"For questions, reply to this email.\n\nBest regards,\n{vendor} Billing"
    )
    return {
        "subject": _pick(subjects),
        "body_text": body,
        "sender_display_name": f"{vendor} Billing",
        "sender_address": f"billing@{attacker}",
        "reply_to": f"billing@{_pick(FREE_SENDERS)}",
        "urls": [url],
        "label": "phishing",
        "source": "synthetic",
        "era_bucket": "recent",
        "subtype": "invoice_fraud",
        "augmented": True,
        "display_from_mismatch": True,
        "reply_to_mismatch": True,
        "free_email_sender": False,
        "url_count": 1,
        "domain_count": 1,
        "shortened_url_present": False,
        "suspicious_tld_present": True,
        "ip_literal_url": False,
        "typosquatting_detected": False,
        "brand_mention": False,
        "sender_brand_mismatch": False,
    }


def _malware_delivery(i):
    n = _n()
    q = random.choice([1, 2, 3, 4])
    subject = _pick(MALWARE_SUBJECTS).format(n=n, q=q)
    attacker = _pick(ATTACKER_DOMAINS)
    url = f"https://{attacker}/doc/{n}.exe"
    bodies = [
        f"Please find the attached document for your review.\n\n"
        f"Download: {url}\n\nThis document requires your immediate attention.",

        f"You have received a scanned document.\n\n"
        f"To view the document, click the link below:\n{url}\n\n"
        f"The document will expire in 48 hours.",

        f"A file has been shared with you.\n\nFile: Report_Q{q}_{n}.docx\n"
        f"Download link: {url}\n\nPlease review and respond at your earliest convenience.",
    ]
    return {
        "subject": subject,
        "body_text": _pick(bodies),
        "sender_display_name": "Document Service",
        "sender_address": f"docs@{attacker}",
        "reply_to": f"noreply@{_pick(FREE_SENDERS)}",
        "urls": [url],
        "label": "phishing",
        "source": "synthetic",
        "era_bucket": "recent",
        "subtype": "malware_delivery",
        "augmented": True,
        "display_from_mismatch": True,
        "reply_to_mismatch": True,
        "free_email_sender": False,
        "url_count": 1,
        "domain_count": 1,
        "shortened_url_present": False,
        "suspicious_tld_present": True,
        "ip_literal_url": False,
        "typosquatting_detected": False,
        "brand_mention": False,
        "sender_brand_mismatch": False,
    }


def _redirect_phishing(i):
    brand, domain = _brand_pair()
    short_url = _redirect_url()
    attacker = _pick(ATTACKER_DOMAINS)
    final_url = _attacker_url("reset")
    subjects = [
        f"Your {brand} session has expired — re-authenticate",
        f"[{brand}] Complete your account setup",
        f"Action needed: {brand} account verification",
        f"Re-verify your {brand} account to continue",
    ]
    body = (
        f"Dear {brand} User,\n\n"
        f"Your session has expired. Please click the link below to re-authenticate "
        f"and continue using your {brand} services.\n\n"
        f"Continue: {short_url}\n\n"
        f"This link will redirect you to our secure portal.\n\n{brand} Team"
    )
    return {
        "subject": _pick(subjects),
        "body_text": body,
        "sender_display_name": f"{brand} Team",
        "sender_address": f"noreply@{attacker}",
        "reply_to": "",
        "urls": [short_url, final_url],
        "label": "phishing",
        "source": "synthetic",
        "era_bucket": "recent",
        "subtype": "redirect_phishing",
        "augmented": True,
        "display_from_mismatch": True,
        "reply_to_mismatch": False,
        "free_email_sender": False,
        "url_count": 2,
        "domain_count": 2,
        "shortened_url_present": True,
        "suspicious_tld_present": True,
        "ip_literal_url": False,
        "typosquatting_detected": False,
        "brand_mention": True,
        "sender_brand_mismatch": True,
    }


# ---------------------------------------------------------------------------
# Spam generator
# ---------------------------------------------------------------------------

SPAM_CATEGORIES = ["saas_promo", "ecommerce", "newsletter", "affiliate", "bulk_mail"]

def _spam(i):
    category = _pick(SPAM_CATEGORIES)
    company = _pick(COMPANIES)
    # i is embedded in the body to guarantee uniqueness across iterations
    tag = f"ref={i:05d}"

    if category == "saas_promo":
        product = random.choice(["CRM Pro", "Analytics Suite", "CloudBackup", "TaskFlow", "SecureVPN"])
        subject = random.choice([
            f"Start your free trial of {product} today",
            f"{product} — 30 days free, no credit card required",
            f"Boost your productivity with {product}",
            f"Special offer: {product} at 40% off this month",
        ])
        body = (
            f"Hi there,\n\n"
            f"We'd like to invite you to try {product} — the easiest way to manage your workflow.\n\n"
            f"✓ 30-day free trial\n✓ No credit card required\n✓ Cancel anytime\n\n"
            f"Start your free trial: https://www.{company.lower().replace(' ','-')}.com/trial?{tag}\n\n"
            f"To unsubscribe, click here: https://www.{company.lower().replace(' ','-')}.com/unsubscribe\n\n"
            f"The {product} Team"
        )
    elif category == "ecommerce":
        discount = random.choice([10, 15, 20, 25, 30, 40, 50])
        subject = random.choice([
            f"Flash sale: {discount}% off everything this weekend",
            f"Your exclusive {discount}% discount — today only",
            f"Don't miss out: {discount}% off sitewide",
            f"Limited time offer: Save {discount}% now",
        ])
        body = (
            f"Hi,\n\n"
            f"For a limited time, enjoy {discount}% off your entire order.\n\n"
            f"Use code: SAVE{discount} at checkout.\n\n"
            f"Shop now: https://shop.{company.lower().replace(' ','-')}.com?{tag}\n\n"
            f"Offer expires Sunday at midnight. Terms and conditions apply.\n\n"
            f"Unsubscribe: https://shop.{company.lower().replace(' ','-')}.com/unsubscribe"
        )
    elif category == "newsletter":
        subject = random.choice([
            f"Your weekly digest from {company}",
            f"{company} Newsletter — Top stories this week",
            f"What's new at {company} this week",
        ])
        body = (
            f"Hello,\n\n"
            f"Here's your weekly roundup from {company}.\n\n"
            f"• Industry news and updates\n• Product announcements\n• Tips and best practices\n\n"
            f"Read more: https://www.{company.lower().replace(' ','-')}.com/newsletter?{tag}\n\n"
            f"You're receiving this because you subscribed to our newsletter.\n"
            f"Unsubscribe: https://www.{company.lower().replace(' ','-')}.com/unsubscribe"
        )
    elif category == "affiliate":
        subject = random.choice([
            f"Earn money recommending products you love",
            f"Join our affiliate program — earn up to 30% commission",
            f"Make money from home with our partner program",
        ])
        body = (
            f"Hi,\n\n"
            f"Join the {company} affiliate program and earn commission on every sale you refer.\n\n"
            f"• Up to 30% commission per sale\n• Real-time tracking dashboard\n• Monthly payouts\n\n"
            f"Sign up: https://affiliates.{company.lower().replace(' ','-')}.com?{tag}\n\n"
            f"Unsubscribe: https://affiliates.{company.lower().replace(' ','-')}.com/unsubscribe"
        )
    else:  # bulk_mail
        subject = random.choice([
            f"Important update from {company}",
            f"You have a message from {company}",
            f"Special announcement from {company}",
        ])
        body = (
            f"Dear Subscriber,\n\n"
            f"We have an important update to share with you from {company}.\n\n"
            f"Please visit our website for full details: https://www.{company.lower().replace(' ','-')}.com?{tag}\n\n"
            f"To unsubscribe from future emails, click here: "
            f"https://www.{company.lower().replace(' ','-')}.com/unsubscribe"
        )

    sender_domain = f"{company.lower().replace(' ','-')}.com"
    return {
        "subject": subject,
        "body_text": body,
        "sender_display_name": company,
        "sender_address": f"newsletter@{sender_domain}",
        "reply_to": "",
        "urls": [f"https://www.{sender_domain}"],
        "label": "spam",
        "source": "synthetic",
        "era_bucket": "recent",
        "subtype": category,
        "augmented": True,
        "display_from_mismatch": False,
        "reply_to_mismatch": False,
        "free_email_sender": False,
        "url_count": 2,
        "domain_count": 1,
        "shortened_url_present": False,
        "suspicious_tld_present": False,
        "ip_literal_url": False,
        "typosquatting_detected": False,
        "brand_mention": False,
        "sender_brand_mismatch": False,
    }


# ---------------------------------------------------------------------------
# Generation plan
# ---------------------------------------------------------------------------

PHISHING_PLAN = [
    ("credential_harvesting", 1200, _credential),
    ("bec_wire_transfer",      250, lambda i: _bec("bec_wire_transfer", i)),
    ("bec_gift_card",          250, lambda i: _bec("bec_gift_card", i)),
    ("bec_invoice_change",     250, lambda i: _bec("bec_invoice_change", i)),
    ("bec_bank_account",       250, lambda i: _bec("bec_bank_account", i)),
    ("bec_payroll_redirect",   250, lambda i: _bec("bec_payroll_redirect", i)),
    ("invoice_fraud",          800, _invoice_fraud),
    ("malware_delivery",       700, _malware_delivery),
    ("redirect_phishing",      700, _redirect_phishing),
]

SPAM_PLAN = [
    ("synthetic_spam", 800, _spam),
]


def _generate(plan, out_dir):
    total = 0
    for subtype, count, fn in plan:
        samples = []
        seen_ids = set()
        i = 0
        attempts = 0
        max_attempts = count * 10  # prevent infinite loop
        while len(samples) < count and attempts < max_attempts:
            rec = fn(i)
            rid = email_id(rec["subject"], rec["body_text"])
            if rid not in seen_ids:
                rec["id"] = rid
                samples.append(rec)
                seen_ids.add(rid)
            i += 1
            attempts += 1
        if len(samples) < count:
            print(f"    Warning: only generated {len(samples)}/{count} unique samples for {subtype}")
        out_path = out_dir / f"{subtype}.json"
        out_path.write_text(json.dumps(samples, indent=2))
        print(f"  {subtype}: {len(samples)} samples → {out_path}")
        total += len(samples)
    return total


def main():
    print("Generating synthetic phishing samples...")
    n_phish = _generate(PHISHING_PLAN, OUT_PHISH)

    print("\nGenerating synthetic spam samples...")
    n_spam = _generate(SPAM_PLAN, OUT_SPAM)

    total_synthetic = n_phish + n_spam
    current_organic = 21_394  # from last build run
    total = current_organic + total_synthetic
    print(f"\nTotal synthetic: {total_synthetic:,}  ({total_synthetic/total:.1%} of projected total {total:,})")
    print("Synthetic cap is 25% — current share is within limit." if total_synthetic/total <= 0.25
          else "⚠️  Synthetic cap exceeded — reduce counts.")
    print("\n✅ Done. Re-run build_dataset.py to incorporate synthetic samples.")


if __name__ == "__main__":
    main()
