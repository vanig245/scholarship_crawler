DB_PATH = "data/scholarships.db"
USER_AGENT = "AtlasScholarshipBot/0.1 (educational assignment; contact: your-email@example.com)"
REQUEST_TIMEOUT = 20
CRAWL_DELAY_SECONDS = 1.5
MAX_CANDIDATES = 100
MAX_HUBS = 20
MAX_LINKS_PER_HUB = 15
SOON_DAYS = 30
VERIFIED_THRESHOLD = 95.0

OFFICIAL_SUFFIXES = {
    ".gov.in": "GOVERNMENT", ".nic.in": "GOVERNMENT",
    ".ac.in": "UNIVERSITY", ".edu.in": "UNIVERSITY", ".edu": "UNIVERSITY",
}

AGGREGATOR_DOMAINS = {
    "buddy4study.com", "scholarshipsindia.com", "scholarships.net.in",
    "vidyasaarathi.co.in", "indiascholarships.com", "medium.com", "quora.com",
    "youtube.com", "facebook.com", "linkedin.com", "twitter.com", "x.com",
    "instagram.com", "wikipedia.org", "reddit.com",
}

AGG_KEYWORDS = ("scholar", "buddy4", "blog", "news", "exam", "career", "jobs", "study", "guide")

SEEDS = [
    "https://scholarships.gov.in/",
    "https://www.aicte-india.org/schemes/students-development-schemes",
    "https://www.ugc.gov.in/",
    "https://www.education.gov.in/",
    "https://socialjustice.gov.in/",
    "https://tribal.nic.in/",
    "https://www.tatatrusts.org/our-work/individual-grants-programmes/education-grants",
    "https://www.buddy4study.com/scholarships",
]

QUERIES = [
    "scholarship for Indian students apply last date 2026-27 site:gov.in",
    "scholarship 2026-27 eligibility apply site:ac.in",
    "post matric scholarship SC ST OBC 2026-27 apply official",
    "scholarship for girl students India 2026 official application",
    "minority students scholarship 2026-27 official notification",
    "CSR scholarship programme India undergraduate students apply 2026",
    "foundation scholarship India meritorious students application 2026",
    "trust scholarship India students apply online 2026",
    "PhD fellowship India 2026 apply official",
    "engineering students scholarship India 2026 AICTE",
]