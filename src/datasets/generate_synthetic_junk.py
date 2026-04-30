"""
Phase 3 — Synthetic Junk generation.

Generates 8,000–12,000 synthetic Junk emails from 5 category templates.
Writes data/interim/synthetic_junk/synthetic_junk.jsonl

Each record has the same schema as enron_junk_candidates.jsonl plus
explicit metadata fields (spf_result, tld_risk_score, etc.) and
augmented=True.

Usage:
    python src/generate_synthetic_junk.py
"""

import json
import random
import re
import uuid
from itertools import product
from pathlib import Path

OUT_FILE = Path("data/interim/synthetic_junk/synthetic_junk.jsonl")
TARGET   = 10_000  # mid-range of 8k–12k

random.seed(42)

# ---------------------------------------------------------------------------
# Shared slot pools
# ---------------------------------------------------------------------------
FIRST_NAMES   = ["James", "Sarah", "Michael", "Emily", "David", "Jessica",
                 "Robert", "Ashley", "William", "Amanda", "Daniel", "Megan"]
LAST_NAMES    = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
                 "Miller", "Davis", "Wilson", "Taylor", "Anderson", "Thomas"]
COMPANIES     = ["Acme Corp", "Pinnacle Solutions", "NexGen Systems", "BlueSky Inc",
                 "Vertex Partners", "Meridian Group", "Apex Consulting", "CoreTech",
                 "Summit Advisors", "Horizon Enterprises", "Catalyst Group", "Vantage Co"]
TITLES        = ["Account Executive", "Business Development Manager", "Sales Director",
                 "Partnership Manager", "Client Success Manager", "Regional Director"]
DOMAINS       = ["solutions.com", "partners.net", "group.com", "advisors.com",
                 "consulting.net", "services.com", "corp.com", "enterprises.com"]
GREETINGS     = ["Hi there", "Hello", "Good morning", "Dear colleague",
                 "Hi", "Greetings", "Dear professional"]
CTA_PHRASES   = ["Let me know if you'd like to connect.",
                 "Would love to schedule a quick call.",
                 "Happy to send over more details.",
                 "Feel free to reply and we can set up a time.",
                 "Looking forward to hearing from you."]
URGENCY_SOFT  = ["Don't miss out.", "Limited spots available.",
                 "Offer ends soon.", "Reserve your spot today.",
                 "Only a few openings left."]

# ---------------------------------------------------------------------------
# Category 1: Consulting solicitations
# ---------------------------------------------------------------------------
CONSULT_SERVICES  = ["IT infrastructure", "cloud migration", "digital transformation",
                     "process optimization", "HR strategy", "supply chain management",
                     "cybersecurity posture", "data analytics", "financial planning"]
CONSULT_BENEFITS  = ["reduce operational costs by 20%", "improve team efficiency",
                     "streamline your workflows", "scale faster",
                     "cut overhead significantly", "boost productivity"]
CONSULT_TEMPLATES = [
    {
        "subject": "Quick question about {service} for {company}",
        "body": (
            "{greeting},\n\n"
            "I came across {company} and wanted to reach out about {service}.\n\n"
            "We've helped companies similar to yours {benefit}. "
            "I'd love to share how we did it.\n\n"
            "{cta}\n\n"
            "Best,\n{sender_name}\n{title}, {sender_company}"
        ),
    },
    {
        "subject": "Helping {company} with {service}",
        "body": (
            "{greeting},\n\n"
            "My name is {sender_name} from {sender_company}. "
            "We specialize in {service} for businesses like {company}.\n\n"
            "Our clients typically see results like: {benefit}.\n\n"
            "{cta}\n\n"
            "Regards,\n{sender_name}\n{title}"
        ),
    },
    {
        "subject": "Thought this might be relevant for {company}",
        "body": (
            "{greeting},\n\n"
            "I wanted to share something that's been helping companies in your space "
            "with {service}.\n\n"
            "We recently helped a client {benefit} — happy to walk you through it.\n\n"
            "{cta}\n\n"
            "Thanks,\n{sender_name}\n{sender_company}"
        ),
    },
    {
        "subject": "Re: {service} — quick intro",
        "body": (
            "{greeting},\n\n"
            "Reaching out because we work with a number of companies on {service} "
            "and thought {company} might benefit.\n\n"
            "We help teams {benefit}. {urgency}\n\n"
            "{cta}\n\n"
            "Best,\n{sender_name}\n{title}, {sender_company}"
        ),
    },
]

def gen_consulting():
    t = random.choice(CONSULT_TEMPLATES)
    sender_first, sender_last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
    sender_company = random.choice(COMPANIES)
    company = random.choice(COMPANIES)
    service = random.choice(CONSULT_SERVICES)
    subj = t["subject"].format(service=service, company=company)
    body = t["body"].format(
        greeting=random.choice(GREETINGS),
        company=company,
        service=service,
        benefit=random.choice(CONSULT_BENEFITS),
        cta=random.choice(CTA_PHRASES),
        urgency=random.choice(URGENCY_SOFT),
        sender_name=f"{sender_first} {sender_last}",
        title=random.choice(TITLES),
        sender_company=sender_company,
    )
    domain = f"{sender_company.lower().replace(' ', '')}.{random.choice(DOMAINS).split('.')[-1]}"
    return subj, body, f"{sender_first.lower()}.{sender_last.lower()}@{domain}", "consulting_solicitation"


# ---------------------------------------------------------------------------
# Category 2: Webinar invites
# ---------------------------------------------------------------------------
WEBINAR_TOPICS  = ["AI in enterprise security", "scaling remote teams in 2024",
                   "modern data pipeline architecture", "zero-trust network design",
                   "B2B sales automation", "cloud cost optimization",
                   "leadership in hybrid work", "product-led growth strategies"]
WEBINAR_DATES   = ["Tuesday, May 14 at 2pm ET", "Thursday, June 6 at 11am PT",
                   "Wednesday, May 22 at 1pm CT", "Friday, May 31 at 3pm ET",
                   "Monday, June 10 at 10am PT"]
WEBINAR_HOSTS   = ["our expert panel", "industry leaders", "our senior team",
                   "top practitioners in the field"]
WEBINAR_TEMPLATES = [
    {
        "subject": "Join us: {topic} — {date}",
        "body": (
            "{greeting},\n\n"
            "You're invited to our upcoming webinar: **{topic}**\n\n"
            "Date: {date}\n"
            "Hosted by: {host}\n\n"
            "In this session we'll cover practical strategies you can apply immediately. "
            "{urgency}\n\n"
            "Register here: https://www.{reg_domain}/webinar/register\n\n"
            "Hope to see you there,\n{sender_name}\n{sender_company}"
        ),
    },
    {
        "subject": "Free webinar: {topic}",
        "body": (
            "{greeting},\n\n"
            "We're hosting a free webinar on {topic} on {date}.\n\n"
            "Join {host} for an in-depth look at what's working right now. "
            "{urgency}\n\n"
            "Save your seat: https://www.{reg_domain}/events\n\n"
            "Best,\n{sender_name}\n{sender_company}"
        ),
    },
    {
        "subject": "You're invited: {topic} ({date})",
        "body": (
            "{greeting},\n\n"
            "We'd love to have you join us for a live session on {topic}.\n\n"
            "When: {date}\n"
            "What to expect: actionable insights from {host}.\n\n"
            "{urgency}\n\n"
            "Register now: https://www.{reg_domain}/register\n\n"
            "See you there,\n{sender_name}\n{sender_company}"
        ),
    },
]

def gen_webinar():
    t = random.choice(WEBINAR_TEMPLATES)
    sender_first, sender_last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
    sender_company = random.choice(COMPANIES)
    reg_domain = sender_company.lower().replace(" ", "") + ".com"
    topic = random.choice(WEBINAR_TOPICS)
    date  = random.choice(WEBINAR_DATES)
    subj = t["subject"].format(topic=topic, date=date)
    body = t["body"].format(
        greeting=random.choice(GREETINGS),
        topic=topic,
        date=date,
        host=random.choice(WEBINAR_HOSTS),
        urgency=random.choice(URGENCY_SOFT),
        reg_domain=reg_domain,
        sender_name=f"{sender_first} {sender_last}",
        sender_company=sender_company,
    )
    domain = f"events.{reg_domain}"
    return subj, body, f"events@{domain}", "webinar_invite"


# ---------------------------------------------------------------------------
# Category 3: Reward / loyalty offers
# ---------------------------------------------------------------------------
POINTS_VALS   = [250, 500, 750, 1000, 1500, 2000, 5000]
REWARD_TYPES  = ["travel miles", "cashback", "store credit", "gift rewards",
                 "loyalty points", "bonus credits"]
REWARD_BRANDS = ["SkyRewards", "PointsPlus", "LoyaltyHub", "RewardZone",
                 "BonusTrack", "MilesAhead", "ValuePoints"]
REDEEM_URLS   = ["rewards.skyrewards.com", "app.pointsplus.com",
                 "portal.loyaltyhub.net", "redeem.rewardzone.com"]
REWARD_TEMPLATES = [
    {
        "subject": "You've earned {points} {reward_type} — redeem now",
        "body": (
            "{greeting},\n\n"
            "Great news! You've earned {points} {reward_type} in your {brand} account.\n\n"
            "Redeem your rewards before they expire: https://{redeem_url}/redeem\n\n"
            "{urgency}\n\n"
            "Your {brand} Team"
        ),
    },
    {
        "subject": "{points} {reward_type} waiting for you",
        "body": (
            "{greeting},\n\n"
            "Your {brand} balance has been updated. "
            "You now have {points} {reward_type} available to redeem.\n\n"
            "Visit your rewards portal: https://{redeem_url}/balance\n\n"
            "{urgency}\n\n"
            "The {brand} Team"
        ),
    },
    {
        "subject": "Congratulations — you've qualified for a {reward_type} bonus",
        "body": (
            "{greeting},\n\n"
            "Congratulations! Based on your recent activity, you've qualified for "
            "a bonus of {points} {reward_type}.\n\n"
            "Claim your bonus here: https://{redeem_url}/claim\n\n"
            "{urgency}\n\n"
            "Best,\nThe {brand} Rewards Team"
        ),
    },
]

def gen_reward():
    t = random.choice(REWARD_TEMPLATES)
    brand = random.choice(REWARD_BRANDS)
    points = random.choice(POINTS_VALS)
    reward_type = random.choice(REWARD_TYPES)
    redeem_url = random.choice(REDEEM_URLS)
    subj = t["subject"].format(points=points, reward_type=reward_type, brand=brand)
    body = t["body"].format(
        greeting=random.choice(GREETINGS),
        points=points,
        reward_type=reward_type,
        brand=brand,
        redeem_url=redeem_url,
        urgency=random.choice(URGENCY_SOFT),
    )
    domain = redeem_url.split(".")[-2] + "." + redeem_url.split(".")[-1]
    return subj, body, f"rewards@{domain}", "loyalty_reward"


# ---------------------------------------------------------------------------
# Category 4: SaaS trial promotions
# ---------------------------------------------------------------------------
SAAS_PRODUCTS  = ["ProjectFlow", "DataSync Pro", "TeamBoard", "InsightIQ",
                  "AutoDeploy", "SecureVault", "AnalyticsHub", "WorkflowAI",
                  "CloudMonitor", "ReportBuilder"]
SAAS_DURATIONS = ["14-day", "30-day", "21-day", "60-day"]
SAAS_FEATURES  = ["real-time dashboards", "automated reporting", "team collaboration tools",
                  "one-click integrations", "AI-powered insights", "unlimited users"]
SAAS_DOMAINS   = ["projectflow.io", "datasyncpro.com", "teamboard.app",
                  "insightiq.co", "autodeploy.io", "securevault.com"]
SAAS_TEMPLATES = [
    {
        "subject": "Start your free {duration} trial of {product}",
        "body": (
            "{greeting},\n\n"
            "We'd like to offer you a free {duration} trial of {product} — "
            "no credit card required.\n\n"
            "With {product} you get: {feature}.\n\n"
            "Start your trial: https://www.{saas_domain}/trial\n\n"
            "{urgency}\n\n"
            "The {product} Team"
        ),
    },
    {
        "subject": "{product} — free trial for your team",
        "body": (
            "{greeting},\n\n"
            "Thousands of teams use {product} for {feature}. "
            "We're offering a free {duration} trial so you can see it in action.\n\n"
            "Get started: https://www.{saas_domain}/free-trial\n\n"
            "{urgency}\n\n"
            "Best,\nThe {product} Team"
        ),
    },
    {
        "subject": "Try {product} free for {duration}",
        "body": (
            "{greeting},\n\n"
            "We built {product} to help teams like yours with {feature}.\n\n"
            "Try it free for {duration}: https://www.{saas_domain}/signup\n\n"
            "{urgency}\n\n"
            "Cheers,\nThe {product} Team"
        ),
    },
]

def gen_saas():
    t = random.choice(SAAS_TEMPLATES)
    product  = random.choice(SAAS_PRODUCTS)
    duration = random.choice(SAAS_DURATIONS)
    feature  = random.choice(SAAS_FEATURES)
    saas_domain = random.choice(SAAS_DOMAINS)
    subj = t["subject"].format(product=product, duration=duration)
    body = t["body"].format(
        greeting=random.choice(GREETINGS),
        product=product,
        duration=duration,
        feature=feature,
        saas_domain=saas_domain,
        urgency=random.choice(URGENCY_SOFT),
    )
    return subj, body, f"hello@{saas_domain}", "saas_trial"


# ---------------------------------------------------------------------------
# Category 5: B2B vendor outreach
# ---------------------------------------------------------------------------
PRODUCT_CATS  = ["office supplies", "IT hardware", "cloud storage solutions",
                 "managed print services", "corporate travel management",
                 "employee benefits platforms", "facility maintenance services",
                 "business insurance", "HR software"]
VENDOR_CLAIMS = ["competitive pricing", "next-day delivery", "dedicated account support",
                 "flexible contracts", "volume discounts", "ISO-certified quality"]
VENDOR_TEMPLATES = [
    {
        "subject": "We supply {product_category} to companies like yours",
        "body": (
            "{greeting},\n\n"
            "My name is {sender_name} from {sender_company}. "
            "We supply {product_category} to businesses across the region.\n\n"
            "We offer {claim} and would love to discuss how we can support {company}.\n\n"
            "{cta}\n\n"
            "Best regards,\n{sender_name}\n{title}, {sender_company}"
        ),
    },
    {
        "subject": "{product_category} — better pricing for {company}",
        "body": (
            "{greeting},\n\n"
            "I wanted to reach out about your {product_category} needs. "
            "At {sender_company} we provide {claim} to companies of all sizes.\n\n"
            "We'd love to put together a proposal for {company}. {urgency}\n\n"
            "{cta}\n\n"
            "Kind regards,\n{sender_name}\n{sender_company}"
        ),
    },
    {
        "subject": "Partnering with {company} on {product_category}",
        "body": (
            "{greeting},\n\n"
            "We work with a number of companies in your sector on {product_category} "
            "and thought {company} might be a great fit.\n\n"
            "Our key differentiator: {claim}.\n\n"
            "{cta}\n\n"
            "Thanks,\n{sender_name}\n{title}, {sender_company}"
        ),
    },
    {
        "subject": "Quick intro — {sender_company} + {company}",
        "body": (
            "{greeting},\n\n"
            "I'm reaching out because we supply {product_category} and have helped "
            "similar companies with {claim}.\n\n"
            "Would love to explore if there's a fit. {urgency}\n\n"
            "{cta}\n\n"
            "Best,\n{sender_name}\n{sender_company}"
        ),
    },
]

def gen_vendor():
    t = random.choice(VENDOR_TEMPLATES)
    sender_first, sender_last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
    sender_company = random.choice(COMPANIES)
    company = random.choice(COMPANIES)
    product_cat = random.choice(PRODUCT_CATS)
    domain = sender_company.lower().replace(" ", "") + ".com"
    subj = t["subject"].format(product_category=product_cat, company=company,
                                sender_company=sender_company)
    body = t["body"].format(
        greeting=random.choice(GREETINGS),
        company=company,
        product_category=product_cat,
        claim=random.choice(VENDOR_CLAIMS),
        cta=random.choice(CTA_PHRASES),
        urgency=random.choice(URGENCY_SOFT),
        sender_name=f"{sender_first} {sender_last}",
        title=random.choice(TITLES),
        sender_company=sender_company,
    )
    return subj, body, f"{sender_first.lower()}.{sender_last.lower()}@{domain}", "vendor_b2b"


# ---------------------------------------------------------------------------
# Validation — discard if any phishing signal present
# ---------------------------------------------------------------------------
PHISHING_CHECK = re.compile(
    r"(verify your|confirm your|enter your (password|login)|"
    r"wire transfer|gift card|invoice payment|"
    r"account (will be|has been) suspended|"
    r"on behalf of the ceo|lookalike)",
    re.IGNORECASE,
)

def is_clean(subject: str, body: str) -> bool:
    return not PHISHING_CHECK.search(subject + " " + body)


# ---------------------------------------------------------------------------
# Metadata assignment (per spec — never derived from text)
# ---------------------------------------------------------------------------
def make_metadata() -> dict:
    return {
        "spf_result":            "pass",
        "dkim_result":           random.choice(["pass", "none"]),  # 50/50
        "dmarc_result":          "none",
        "sender_domain_age_days": random.randint(365, 3650),
        "tld_risk_score":        1,
        "reply_to_mismatch":     False,
        "html_text_ratio":       round(random.uniform(0.3, 2.0), 4),
        "url_count":             random.randint(1, 5),
        "attachment_count":      0,
        "sender_seen_before":    False,
        "first_time_domain":     True,
        "communication_frequency": 0,
        "send_hour_deviation":   round(random.gauss(0, 3), 2),  # realistic dist
        "domain_age_reliable":   True,
        "augmented":             True,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
GENERATORS = [gen_consulting, gen_webinar, gen_reward, gen_saas, gen_vendor]

def main():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    per_category = TARGET // len(GENERATORS)  # ~2,000 each
    generated, discarded = 0, 0
    category_counts = {}

    with open(OUT_FILE, "w", encoding="utf-8") as outf:
        for gen_fn in GENERATORS:
            cat_count = 0
            attempts  = 0
            while cat_count < per_category:
                attempts += 1
                if attempts > per_category * 10:
                    print(f"  Warning: {gen_fn.__name__} hit attempt limit")
                    break
                subject, body, from_address, category = gen_fn()
                if not is_clean(subject, body):
                    discarded += 1
                    continue
                record = {
                    "file":                 f"synthetic/{category}/{uuid.uuid4().hex[:8]}",
                    "subject":              subject,
                    "body_text":            body,
                    "sender_display_name":  "",
                    "from_address":         from_address,
                    "to_address":           "",
                    "date":                 "",
                    "headers":              {},
                    "urls":                 [],
                    "attachments":          [],
                    "label":                "junk",
                    "category":             category,
                    **make_metadata(),
                }
                outf.write(json.dumps(record) + "\n")
                cat_count += 1
                generated += 1

            category_counts[category] = cat_count

    print(f"Generated : {generated:,}")
    print(f"Discarded : {discarded:,}")
    print(f"Per category: {category_counts}")
    print(f"Output: {OUT_FILE}")


if __name__ == "__main__":
    main()
