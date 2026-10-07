# Scholarship Intelligence Crawler

An autonomous, AI-powered web crawler and data pipeline designed to discover, extract, and verify education funding opportunities for Indian students. 

Unlike standard web scrapers, this system functions as an intelligence engine. It dynamically discovers new scholarship portals, extracts unstructured data into a rigid schema using LLMs, grounds every data point with exact verbatim evidence to prevent hallucinations, and runs a deterministic confidence-scoring algorithm to verify authenticity.

## Key Features

* **Autonomous Discovery Engine:** Dynamically expands beyond hard-coded seed URLs by utilizing live search queries to find new government, university, and corporate CSR scholarships.
* **Zero-Hallucination Extraction:** Utilizes advanced LLM structured output parsing. Every extracted field (deadline, amount, eligibility) is mathematically grounded to an exact `evidence_quote` from the source DOM.
* **Deterministic Verification & Scoring:** Generates a rigorous Confidence Score for every record based on source authority (official vs. aggregator), evidence completeness, and actionability. Records only achieve `VERIFIED` status if confidence is ≥95%.
* **Continuous Change Detection:** Built for continuous cron-style execution. Detects updates to existing scholarships (e.g., extended deadlines) and maintains an immutable audit log of old vs. new values.
* **Stale Data Pruning:** Automatically flags scholarships that have expired, been removed from official sources, or can no longer be verified.
* **Integrated Web Dashboard:** A lightweight web interface to query the database, inspect evidence quotes, and monitor the pipeline's operational metrics.

## System Architecture

The pipeline follows a strict, unidirectional data flow optimized for data integrity:

`Discover` $\rightarrow$ `Classify` $\rightarrow$ `Fetch` $\rightarrow$ `Extract` $\rightarrow$ `Verify` $\rightarrow$ `Store` $\rightarrow$ `Update`

1. **Crawler (`crawler/`):**
   * `discover.py`: Ingests seed URLs and search queries to find new potential nodes.
   * `classify.py`: Evaluates domain authority (e.g., `.gov.in`, `.ac.in`) to separate authoritative primary sources from aggregators.
   * `fetch.py`: Handles polite HTTP requests, timeouts, and DOM parsing.
   * `extract.py`: Schema-driven LLM extraction that maps raw text to structured fields with evidence tracing.
   * `verify.py`: The deterministic rule engine that calculates the final confidence score.
   * `pipeline.py`: The orchestrator that manages state, triggers change detection, and handles database commits.
2. **Database (`db.py`):** SQLite database utilizing three core tables: `scholarships` (current state), `evidence` (anti-hallucination trace logs), and `change_log` (historical mutation tracking).
3. **Application (`app/`):** A backend server routing data to a front-end dashboard for real-time intelligence monitoring.

## Repository Structure

```text
scholarship-crawler/
├── app/
│   ├── main.py              # Web application server and API routes
│   └── static/
│       └── index.html       # Dashboard UI
├── crawler/
│   ├── __init__.py
│   ├── classify.py          # Domain authority classification
│   ├── discover.py          # Dynamic URL discovery 
│   ├── extract.py           # Data extraction and evidence grounding
│   ├── fetch.py             # Web request and parsing logic
│   ├── pipeline.py          # Main orchestration and change detection
│   └── verify.py            # Confidence scoring engine
├── data/
│   └── scholarships.db      # Pre-populated SQLite database
├── .gitignore
├── config.py                # System parameters, seeds, and thresholds
├── db.py                    # Database schema and query helpers
├── README.md                # Project documentation
├── requirements.txt         # Python dependencies
└── run.py                   # CLI entry point


## Tech Stack
* **Language:** Python 3.10+
* **Data Processing & AI:** LangChain / Pydantic (Structured Extraction), DuckDuckGo Search (Discovery)
* **Backend & UI:** FastAPI / Flask (App Server), HTML/CSS (Static UI)
* **Database:** SQLite3

## Setup and Installation

**1. Clone the repository**
```bash
git clone [https://github.com/vanig245/scholarship_crawler.git]
cd scholarship_crawler


## Create and activate a virtual environment
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate