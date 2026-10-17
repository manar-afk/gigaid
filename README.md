# Gig-Aid (साथी / Gig Worker AI Grievance Assistant)

> **Gig-Aid** is a pan-India, multilingual GenAI grievance assistant for gig and informal workers, including delivery partners, drivers, and daily-wage workers. It helps workers describe a pay, penalty, account, or workplace dispute in their preferred language, asks for missing details, and creates a clear, editable grievance draft based on the worker’s own account. It explains relevant verified guidance in simple language and provides source links where available. Workers stay in control of reviewing and submitting their complaint.

---

## 1. Core Principles & Safeguards

- **Creates Clear Grievance Drafts Based on Worker-Provided Facts**:
  The assistant explicitly distinguishes between:
  1. **Worker-provided facts**: What the worker described in their own report.
  2. **Guidance verified from an official source**: Sourced from official Central Government or State portals.
  3. **Information it could not verify**: Unconfirmed claims, missing employer rules, or unverified timelines.
  The assistant **does not invent** laws, deadlines, evidence, platform policies, or likely outcomes. If guidance cannot be verified, it says so and still helps produce a neutral draft.

- **Pan-India Guidance with State Verification**:
  Nationwide guidance is grounded in verified central sources (e.g., e-Shram portal, National Consumer Helpline 1915, IT Rules Grievance Redressal). The assistant asks for the worker's state before offering state-specific rights or schemes. State-specific information (such as the Rajasthan 2023 Act or the Karnataka 2025 Act, Act 72 of 2025) is included only when verified from official sources and clearly labeled with the state. If applicable guidance cannot be confirmed, it says so.

- **Worker-Controlled Next Steps**:
  The worker can review and edit the draft, copy or download it, and open verified official contact or grievance information. The assistant prepares a draft; it does not claim a complaint has been submitted or guarantee a resolution.

- **Concrete Privacy & Security Behavior**:
  - Collects only details needed to prepare the grievance draft; workers can omit identifying information.
  - Explains when text is sent to the AI provider.
  - Does not retain grievance text by default (stateless request handling).
  - API keys and deployment credentials stored in managed secrets.
  - Input size and schema validation, restricted CORS, safe error messages without stack trace leaks.
  - PII masking applied as a defense-in-depth layer to reduce accidental exposure, with an explicit note that regex masking may not catch every sensitive detail.
  - User input and external text treated as untrusted content, defended against embedded prompt-injection instructions.

- **Accessibility & Safety**:
  Optional speech input and audio readout are available in supported browsers and languages. Typing and editing remain fully available if speech features are unavailable. The interface supports keyboard and screen-reader use, readable contrast, clear recording and playback controls, and large touch targets (48px+). **It does not encourage use while driving or operating equipment.**

- **Configurable Model Settings**:
  Uses a currently supported, configurable Gemini model (e.g., `gemini-2.5-flash`). Model names and provider settings are maintained in configuration.

---

## 2. Evaluation Criteria Alignment

| Evaluation Parameter | How Gig-Aid Addresses It |
| :--- | :--- |
| **1. Code Quality** | Clean, modular codebase (`backend/routers`, `backend/services`, `backend/schemas`, `backend/config`). Strict Pydantic models for validation, 100% type-hinted Python, separation of concerns. |
| **2. Problem Statement Alignment** | Directly tackles the primary vulnerability of Indian gig workers: unfair penalties, arbitrary deactivations, and withheld payouts. Delivers multilingual intake, missing-fact clarification, neutral drafting, and verified source guidance. |
| **3. Security** | Minimal data collection, safe secret handling via managed secrets, input size validation (max 4000 chars), PII exposure reduction, safe error responses without stack traces, and prompt injection delimiter wrapping. |
| **4. Efficiency** | Bounded inputs and outputs, single-call structured prompts, sensible network timeouts (30s), lightweight vanilla frontend with zero heavy node dependencies. |
| **5. Testing** | Comprehensive automated `pytest` suite covering: successful drafts, missing info queries, unsupported claims handling, model fallback, schema validation, and privacy safeguards. |
| **6. Accessibility** | Full text-only editing, keyboard navigation (`:focus-visible`), screen reader support (semantic HTML, skip links, aria attributes), high contrast for outdoor readability, large touch targets (48px+), and optional speech features. |

---

## 3. System Architecture & Project Layout

```
gig-aid/
├── Dockerfile                  # Production Cloud Run container (non-root, $PORT)
├── .dockerignore               # Clean build context
├── .env.example                # Configuration template
├── README.md                   # Complete documentation & Cloud Run manual guide
├── requirements.txt            # Minimal, pinned dependencies
├── backend/
│   ├── main.py                 # FastAPI app, security headers, CORS, /health
│   ├── config.py               # Pydantic Settings (configurable model, timeouts, secrets)
│   ├── schemas.py              # Pydantic request/response models & validators
│   ├── routers/
│   │   └── grievance.py        # /api/v1/grievance endpoints (intake, sources)
│   └── services/
│       ├── llm_service.py      # Configurable Gemini integration, fact/source separation, fallback
│       ├── safety_guard.py     # PII exposure reduction, prompt-injection defense, sanitization
│       └── official_sources.py # Verified Central & State portals (e-Shram, NCH, Rajasthan, Karnataka)
├── frontend/
│   ├── index.html              # Accessible, high-contrast, mobile-first interface
│   ├── css/
│   │   └── styles.css          # WCAG AAA compliant contrast, 48px touch targets
│   └── js/
│       └── app.js              # Worker-controlled flow, Web Speech STT/TTS, copy/download
└── tests/
    ├── test_api.py             # Route tests: health, sources, validation errors, intake
    ├── test_security.py        # PII reduction, prompt injection, input bounds
    ├── test_official_sources.py# Pan-India vs State-specific source lookup tests
    └── test_llm_service.py     # Fact/source separation, fallback, missing fact questions
```

---

## 4. Local Setup & Testing

### Prerequisites
- Python 3.10+ (tested on Python 3.11 and 3.13)
- `pip`

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional: add your `GEMINI_API_KEY` in `.env`. If omitted, Gig-Aid operates using its deterministic grounded generator for local testing and offline verification.)*

### Step 3: Run the Test Suite
```bash
pytest -v
```
*(All 21 automated tests cover API endpoints, security sanitization, PII masking, official source separation, and fallback logic.)*

### Step 4: Start the Local Server
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```
Open your browser at `http://localhost:8080`.

---

## 5. Manual Google Cloud Deployment Guide (Google Cloud Run)

Gig-Aid is containerized and built to run on **Google Cloud Run** using managed secrets and dynamic `$PORT` binding.

### Step 1: Authenticate with Google Cloud
```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
```

### Step 2: Store API Key in Google Secret Manager
Store your API key securely rather than hardcoding or passing it on the command line:
```bash
echo -n "YOUR_ACTUAL_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
```

### Step 3: Deploy to Google Cloud Run
Deploy directly from source:
```bash
gcloud run deploy gig-aid \
  --source . \
  --region asia-south1 \
  --port 8080 \
  --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest \
  --set-env-vars ENVIRONMENT=production,GEMINI_MODEL=gemini-2.5-flash
```

### Step 4: Verify Deployment & Health Check
Cloud Run will output your Service URL (e.g. `https://gig-aid-xxxx.a.run.app`).
Verify the service health:
```bash
curl https://gig-aid-xxxx.a.run.app/health
```
Expected response:
```json
{
  "status": "healthy",
  "service": "Gig-Aid",
  "environment": "production",
  "model_configured": "gemini-2.5-flash"
}
```

---

## 6. Official Sources Referenced

1. **e-Shram Portal**: Ministry of Labour & Employment, Government of India (`https://eshram.gov.in/`) — Helpline: 14434.
2. **National Consumer Helpline**: Department of Consumer Affairs, Government of India (`https://consumerhelpline.gov.in/`) — Toll-free: 1915.
3. **Information Technology (Intermediary Guidelines) Rules, 2021**: Ministry of Electronics and IT, Government of India (`https://www.meity.gov.in/`).
4. **Rajasthan Platform Based Gig Workers Act, 2023**: Passed July 2023.
5. **Karnataka Platform-Based Gig Workers (Social Security and Welfare) Act, 2025 (Act 72 of 2025)**: Passed by Karnataka Legislature (following the 2024 draft bill).
