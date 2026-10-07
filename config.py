DB_PATH = "data/scholarships.db"
USER_AGENT = "AtlasScholarshipBot/0.1 (educational assignment; contact: your-email@example.com)"
REQUEST_TIMEOUT = 20
CRAWL_DELAY_SECONDS = 1.5
MAX_CANDIDATES = 100
MAX_HUBS = 20
MAX_LINKS_PER_HUB = 15
SOON_DAYS = 30
VERIFIED_THRESHOLD = 95.0
MAX_PAGES = 200
MAX_DEPTH = 2

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
    "scholarship India students apply 2026 site:gov.in",
    "scholarship site:ac.in apply eligibility 2026",
    "post matric scholarship SC ST OBC apply",
    "girl students scholarship India apply 2026",
    "minority scholarship India notification 2026",
    "CSR scholarship India students apply",
    "foundation scholarship India students apply",
    "trust scholarship India students apply online",
    "PhD fellowship India apply",
    "AICTE scholarship engineering students",
    "Reliance Foundation scholarships apply",
    "HDFC Parivartan ECSS scholarship",
    "Aditya Birla scholarship apply",
    "Infosys Foundation scholarship apply",
]