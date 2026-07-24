# Company Intelligence & Lead Discovery Platform MVP

An Asynchronous company research engine built with FastAPI, Celery, Redis, PostgreSQL, SearXNG, and Next.js.

## Architecture

- **Backend**: FastAPI (Python 3.11) providing RESTful API and WebSockets for real-time stage updates.
- **Task Queue**: Celery with Redis broker running an 8-stage asynchronous processing chain.
- **Database**: PostgreSQL 16 with hybrid relational & JSONB schema (`stage_results` GIN indexed).
- **Search Engine**: SearXNG self-hosted metasearch instance (no external search API keys required).
- **Frontend**: Next.js 16 (App Router), TypeScript, Tailwind CSS, shadcn/ui.

## 8-Stage Execution Pipeline

1. **Company Discovery**: Multi-query search via SearXNG & fuzzy name matching score. Supports user disambiguation when candidate scores are close.
2. **Website Verification**: Multi-factor signal extraction (title, meta tags, about/contact pages, footer copyright, JS-shell detection).
3. **LinkedIn Presence**: Targeted SearXNG & outbound domain corroboration.
4. **Founder Discovery**: Heuristic extraction of key decision makers (Founder, CEO, MD) from company pages & search snippets.
5. **Contact Enrichment**: Published website emails/phones (Tier 1) & MX-verified pattern guessing (Tier 2).
6. **Facebook Presence**: Outbound link checking & targeted search.
7. **Instagram Presence**: Outbound link checking & targeted search.
8. **Meta Advertising**: Meta Ad Library API integration with web search fallback.
9. **Aggregation**: Overall confidence rating & report generation.

## Getting Started

### Prerequisites

- Docker & Docker Compose

### Running with Docker Compose

1. Navigate into the project folder:
   ```bash
   cd CompanyLookup
   ```

2. Copy environment variable template:
   ```bash
   cp .env.example .env
   ```

3. Build and launch all services: local
   ```bash
   docker-compose up --build -d
   ```

3. Build and launch all services: Prod
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```

4. Run database migrations:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

### Service URLs

- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Celery Flower Dashboard**: [http://localhost:5555](http://localhost:5555)
- **SearXNG Metasearch Engine**: [http://localhost:8080](http://localhost:8080)
