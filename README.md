# NIRNAY
AI-powered financial content verfication and literacy engine for Indian retail investors.

## Architecture

- `frontend/`: Next.js App Router, React, strict TypeScript, and Tailwind CSS. The home page demonstrates consent-based claim extraction, retrieval, assessment, and explanations.
- `backend/`: FastAPI exposes `GET /health`, `POST /api/v1/analyze`, `POST /api/v1/evidence`, and the end-to-end `POST /api/v1/analyze/complete`.
- The analysis service normalizes input and redacts obvious email, Indian phone, PAN, and Aadhaar identifiers locally before handing sanitized text to a replaceable hosted-LLM claim extractor.
- The extractor returns atomic factual, financial, or promotional claims only. It does not assess truth, retrieve evidence, flag scams, or give investment advice.
- The evidence service queries a replaceable search-provider interface once per extracted claim and returns up to three results, independently ranked by deterministic source tier, lexical relevance, snippet availability, and publication date. Tier 1 is assigned only by known regulator/exchange domains and Government of India domains, never by titles or snippets. The API identifies each source as `live_search` or `demo_fixture`.
- Tavily requests raw source-page content when available. A deterministic lexical-overlap extractor selects a short relevant sentence (up to 2,000 characters) for evidence; it does not send whole pages to the assessor. Provider-only raw content is excluded from model serialization and API results. When page content is missing, the system retains explicitly labeled search-snippet semantics; unrelated page text is not emitted as a relevant excerpt.
- Set `EVIDENCE_PROVIDER=fixture` to select deterministic, clearly labeled illustrative results for the suspicious-message demo without changing the frontend. The default is `tavily` live search; demo fixture results are never labeled live.
- Complete assessments are evidence-grounded: a replaceable hosted assessment provider receives only one claim and its ranked evidence package, never the original pasted content. Strict output models and deterministic evidence-ID/source-quality checks reject invalid references and prevent snippet-only or fixture evidence from being presented as directly supported or contradicted.
- A separate deterministic manipulation-signal service scans original content and individual claims for inspectable language patterns (guaranteed returns, urgency, scarcity/FOMO, authority claims, insider language, exaggerated certainty, testimonials/social proof, and promotional numerical claims). It emits neutral matched-text alerts only; it does not affect the evidence assessment and has no risk score.
- Original input and redacted text are held only in request memory; this foundation has no database or content persistence.
- `.env.example`: frontend API URL, CORS origins, and backend-only hosted LLM/search provider configuration.

## Local setup

Requirements: Node.js 20.9 or newer, npm, and Python 3.10 or newer.

Use the values in `.env.example` when setting the environment variables in the shells running each service; the root `.env` file is intentionally not loaded automatically. Set `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, and `TAVILY_API_KEY` only in the backend process. Never set or expose a provider key in a `NEXT_PUBLIC_` variable.

### Start the backend

From the repository root, in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
$env:LLM_API_KEY = "your-provider-key"
$env:LLM_BASE_URL = "https://api.openai.com/v1"
$env:LLM_MODEL = "gpt-4o-mini"
$env:TAVILY_API_KEY = "your-search-provider-key"
$env:EVIDENCE_PROVIDER = "tavily" # use "fixture" for the static demo provider
python -m uvicorn app.main:app --reload
```

The service listens at `http://127.0.0.1:8000`; health check: `http://127.0.0.1:8000/health`.

### Start the frontend

In a second PowerShell window, from the repository root:

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

Open `http://localhost:3000`, paste financial content, select the external-processing consent checkbox, and click **Analyze**. The complete pipeline extracts claims, retrieves evidence, assesses each claim using only its ranked evidence package, and independently detects manipulation-language signals using deterministic rules. Consent covers sending redacted content to the hosted AI for claim extraction, claims to the search provider, and each claim plus its ranked evidence package to the assessment provider. The original pasted content is not sent to the assessment provider; manipulation detection runs locally in the backend. The configured CORS origins allow both common local frontend hostnames. The analyze request is limited to 20,000 characters; obvious identifiers are redacted locally before extraction. Processing does not run without explicit consent.

`POST /api/v1/analyze` accepts `{"content":"...", "consent":true}` and responds with an analysis ID, completion status, and typed claims. It returns no evidence or truth assessment. Without consent it returns HTTP 403; invalid or oversized input returns HTTP 422. A missing LLM key returns HTTP 503, and provider failures or unusable output return HTTP 502.

`POST /api/v1/evidence` accepts up to 10 typed claims and `consent: true`; it queries each claim and responds with source title, URL, domain, source tier, evidence excerpt/status, publication date, and live/demo origin. Results are ordered by an inspectable deterministic ranking function. No source reliability or truth assessment is returned. Missing consent returns HTTP 403, invalid input returns HTTP 422, missing search configuration returns HTTP 503, and provider failures or malformed output return HTTP 502.

`POST /api/v1/analyze/complete` accepts the same content/consent body as `/api/v1/analyze` and returns `results[]`, each containing a typed claim, an assessment (`Supported`, `Contradicted`, `Unverified`, or `Needs more evidence`), rationale, evidence IDs used, uncertainty, and the complete ranked evidence package. Nonempty evidence citations are required for Supported/Contradicted; every ID must exist in that claim's evidence package. With no retrieved evidence, the service deterministically returns Unverified without calling the assessment provider. Search snippets and demo fixtures cannot yield Supported/Contradicted.

For example, the demo text “SEBI approved XYZ investment plan. Guaranteed 30% return. Only 200 slots remaining. Join NOW!” should yield separate claims for the approval assertion, the guaranteed return, and the remaining-slot assertion. The exact phrasing can vary; the claims must remain distinct.

## Tests and production build

Run backend tests from `backend/`:

```powershell
python -m pytest
```

Run frontend typecheck and production build from `frontend/`:

```powershell
npm run typecheck
npm run build
```

After building, serve the production frontend with `npm run start` from `frontend/`.
