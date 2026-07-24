# Executive Technical Architecture Explanation

### 1. High-Level Architecture Overview
> *"We built an end-to-end, event-driven microservice architecture for autonomous company intelligence and lead discovery. The system is designed to execute multi-stage OSINT (Open-Source Intelligence) gathering asynchronously without relying on slow or expensive third-party database APIs."*

- **Frontend**: Built with **Next.js (App Router)**, **TypeScript**, and **TailwindCSS**, utilizing WebSocket streams for real-time stage progress updates.
- **API & Orchestration Layer**: Powered by **FastAPI (Python 3.11/3.14)** with async endpoints and OpenAPI spec integration.
- **Distributed Task Engine**: **Celery worker processes** backed by **Redis** as a message broker for concurrent pipeline stage execution.
- **Persistence Layer**: **PostgreSQL** with **SQLAlchemy ORM** tracking relational entities (`Companies`, `LookupJobs`, `StageResults`).
- **Search Provider Layer**: Self-hosted **SearXNG meta-search engine** containerized locally, allowing non-rate-limited queries across public web indexes.

---

### 2. Deep Dive: 8-Stage Asynchronous Pipeline Engine

> *"When a lookup request is created, FastAPI pushes an umbrella job to Celery, which orchestrates 8 isolated worker sub-tasks running in parallel and sequential dependencies:"*

1. **Stage 1: Entity Resolution & Disambiguation (`company_discovery.py`)**
   - Applies string similarity algorithms (**Jaro-Winkler & Levenshtein distance metrics**) against domain tokens and search snippets.
   - If confidence falls below strict thresholds, it dynamically flags the job status as `NEEDS_INPUT` to trigger human-in-the-loop candidate picking.

2. **Stage 2: First-Party Website Signal Extraction (`website_verification.py`)**
   - Performs live HTTP/HTTPS reachability probes with browser-emulated user agents.
   - Uses DOM parsing to inspect `<title>`, OpenGraph meta tags, footer copyrights, `/about` pages, and `/contact` pages.
   - Extracts published emails and phone numbers directly from site markup.

3. **Stage 3: Corporate Social Discovery (`linkedin_discovery.py`)**
   - Queries exact search engine operators (`site:linkedin.com "{brand_name}"`) and inspects `/company/` and `/school/` URL structures.
   - Corroborates domain strings in URL slugs (e.g. `linkedin.com/company/chaicodehq`).

4. **Stage 4: C-Suite & Founder Identification (`founder_discovery.py`)**
   - Dual-source extraction: Parses site `/about` page HTML for leadership titles (CEO, Founder, MD, CTO) and corroborates with professional profile search queries (`site:linkedin.com/in`).

5. **Stage 5: Multi-Tiered Contact Enrichment (`contact_enrichment.py`)**
   - **Tier 1 (First-Party)**: Verifies raw emails extracted from website HTML.
   - **Tier 2 (DNS Validation)**: Performs real-time MX record lookups via `dnspython` and generates pattern guesses (`first.last@domain.com`).
   - **Tier 3 (Web Snippet Fallback)**: Runs regex pattern matching against search engine snippets.

6. **Stage 6 & 7: Social Footprint Detection (`facebook_presence.py`, `instagram_presence.py`)**
   - Discovers platform profile links and evaluates handle similarity.

7. **Stage 8: Ad Activity Detection (`meta_ads.py`)**
   - Queries Meta Ad Library indexes to confirm active ad campaigns.

---

### 3. Weighted Multi-Factor Scoring Model (`scoring.py` & `aggregator.py`)

> *"Rather than returning raw text search results, our engine evaluates signal weightings to produce deterministic confidence scores:"*

- **Weighted Signal Matrix**: Each stage computes score additions (e.g., Live HTTP 200 = +25, Domain Match = +40, Outbound Link = +35).
- **Confidence Mapping**:
  - **80 – 100**: `High` (`Verified` / `Confirmed`)
  - **50 – 79**: `Medium` (`Probable` / `Likely`)
  - **0 – 49**: `Low` (`Uncertain` / `Not Found`)
- **Aggregator Task**: Once all 8 Celery worker sub-tasks complete, the `aggregator` computes the total weighted score and updates `job.status` to `COMPLETE`.

---

### 4. Real-Time Event Sync & Frontend Optimization

> *"To keep UI responsiveness smooth without clogging the network:"*

- **Redis Pub/Sub & WebSockets**: Worker stages publish completion events to Redis channels (`job:{job_id}`), which FastAPI streams to the browser via WebSockets.
- **Smart Polling Fallback**: The Next.js client uses decoupled React hooks—polling runs strictly while `lookup.status` is `RUNNING` or `PENDING` and **stops 100% permanently** as soon as `COMPLETE` status is reached.

---

### 5. Infrastructure & Containerization

> *"The entire solution is 100% containerized with Docker & Docker Compose for seamless one-command deployment (`docker-compose up --build`):"*

- `companylookup-backend` (FastAPI API server)
- `companylookup-worker` (Celery background process)
- `companylookup-redis` (In-memory pub/sub & message broker)
- `companylookup-db` (PostgreSQL relational database)
- `companylookup-searxng` (Self-hosted search engine)
- `companylookup-frontend` (Next.js web client)

---

### Cheat Sheet Summary:
> *"We built an event-driven, containerized microservice pipeline using **Next.js**, **FastAPI**, **Celery**, **Redis**, and **PostgreSQL**. It runs an 8-stage asynchronous discovery process using a self-hosted search engine, validates domain MX records, extracts C-Suite decision-makers, computes weighted confidence scores, and streams updates to the frontend via WebSockets."*