# AROHAN-ST (आरोहण-ST)
### Configurable Scholarship & Fellowship Management Platform for Scheduled Tribe (ST) Students
**MoTA schemes: NFST, NOS, Top Class, Post-Matric, and Pre-Matric**

---

## 🏛️ Overview

**AROHAN-ST** streamlines the application, pre-screening, and adjudication process for higher education scholarships and fellowships offered to Scheduled Tribe students by the Ministry of Tribal Affairs (MoTA), Government of India:

1. **NFST**: National Fellowship for eligible ST research scholars in India.
2. **NOS**: National Overseas Scholarship for eligible ST students studying abroad.
3. **Top Class Education**: Scholarship for eligible ST students at Ministry-notified premier institutes.
4. **Post-Matric Scholarship**: Centrally Sponsored support for eligible recognized post-secondary courses.
5. **Pre-Matric Scholarship**: Centrally Sponsored support for eligible ST school students.

The platform combines configurable eligibility checks, PDF/image text extraction, applicant correction and tracking, and officer review. It includes **real accounts with bcrypt-hashed passwords**, private application-document access, decision/audit and notification records, an advisory marks-based ranking desk, scheme dashboard/CSV reporting, and award/payment milestone tracking.

**All data lives in MongoDB.** Uploaded and seeded documents are stored in GridFS inside the same database, so there is no local upload directory and no public static file route.

> Automated checks, text extraction, and ranking are **administrative aids only**. They do not authenticate documents, establish entitlement, or make final award decisions. A recorded human officer decision is always required.

---

## 🔐 Accounts and Access

There are two roles, and the role is always taken from the server response — never from the email address.

### Applicant — self-registration

Applicants create their own account from the portal's **Register** tab. No shared code, no pre-provisioned list.

- Password is hashed with bcrypt and never stored or logged in plaintext.
- Password policy: at least `MIN_PASSWORD_LENGTH` (default 8) characters, combining at least two of lowercase, uppercase and digits, and must not contain the email address.
- A registered applicant can only ever read or change their own applications and documents.
- Duplicate email registration is refused with `409`.

### Officer — bootstrapped from the environment

The first officer account is created on start-up from `.env`, and is never overwritten afterwards:

```
BOOTSTRAP_OFFICER_EMAIL=
BOOTSTRAP_OFFICER_PASSWORD=
BOOTSTRAP_OFFICER_NAME=MoTA Officer
```

> **Set a strong, unique officer password before deploying.** Anyone holding it has full adjudication access. Change it by updating the stored account, not by editing `.env` — `.env` only seeds a fresh database.

### Session handling

`POST /auth/login` returns an HMAC-signed bearer token. On every request the backend re-reads the account, so a token is rejected if the account was deleted, deactivated, or had its role changed. Repeated failed sign-ins are throttled per account and client address.

---

## 📁 Repository Structure

```
arohan-st/
├── backend/
│   ├── config.py                       # Centralised settings loaded from the root .env
│   ├── database.py                     # Mongo client, collections, counters, indexes
│   ├── main.py                         # FastAPI entrypoint, lifespan, health & CORS
│   ├── security.py                     # bcrypt, signed sessions, throttling, role guards
│   ├── requirements.txt
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py                   # Status sets and Mongo document builders
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py                  # Pydantic request/response models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── schemes.py                  # GET /schemes, /schemes/code/{code}, /schemes/{id}
│   │   ├── auth.py                     # Registration, sign-in, profile
│   │   ├── applications.py             # Submit, upload, correct, track, withdraw
│   │   ├── admin.py                    # Review, audit, ranking, dashboard, reports, awards
│   │   └── private_documents.py        # Applicant-owned / officer-authorised file streaming
│   ├── services/
│   │   ├── __init__.py
│   │   ├── repository.py               # Mongo queries, payload assembly, audit, awards
│   │   ├── storage.py                  # GridFS upload, stream, metadata, delete
│   │   ├── rule_engine.py              # Configured eligibility checks
│   │   └── ocr_service.py              # PDF/image text extraction and field parsing
│   ├── tests/
│   │   ├── test_security.py            # Hashing, tokens, throttling, role guards
│   │   ├── test_ocr_service.py         # Extraction from bytes and PDF
│   │   ├── test_seed_documents.py      # Seeded register, fixtures, scheme config
│   │   └── test_officer_workflow.py    # Full officer workflow against a throwaway DB
│   ├── utils/
│   │   ├── __init__.py
│   │   └── seed.py                     # Scheme + reference register seeder (MongoDB/GridFS)
│   └── data/scheme_configs/            # nfst, nos, top_class, post_matric, pre_matric
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── main.tsx                    # React DOM mount with AuthProvider
│       ├── App.tsx                     # Portal container & view switcher
│       ├── index.css
│       ├── api/
│       │   ├── client.ts               # Fetch wrapper, bearer token, typed endpoints
│       │   └── types.ts                # TypeScript interfaces
│       ├── hooks/
│       │   └── useAuth.tsx             # Session restore, sign-in, registration, sign-out
│       ├── components/
│       │   ├── Header.tsx              # MoTA masthead, identity, role chip
│       │   ├── Navbar.tsx              # Role-aware navigation and sign-out
│       │   ├── StatusBadge.tsx         # Colour-coded status chip
│       │   └── ConfidenceMeter.tsx     # Rule-check indicator
│       └── pages/
│           ├── applicant/
│           │   ├── ApplicantLogin.tsx  # Sign-in / registration
│           │   ├── SchemeSelection.tsx # Configured MoTA scheme catalogue
│           │   ├── ApplicationForm.tsx # Dynamic scheme form & document upload
│           │   └── StatusTracker.tsx   # Stage timeline, correction, withdrawal
│           └── admin/
│               ├── ReviewQueue.tsx     # Paginated review dashboard and reports
│               ├── ApplicationDetail.tsx # Decision, documents, audit history
│               ├── SelectionDesk.tsx   # Advisory marks ranking and human review
│               └── AwardManagement.tsx # Award lifecycle and payment milestones
└── docs/
    └── sample-documents/               # Source fixtures read once and written into GridFS
```

---

## ⚙️ Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+ and npm
- A reachable MongoDB instance (Atlas SRV or self-hosted)
- Optional: Tesseract OCR on `PATH` for scanned images (digital PDFs and TXT files use local text extraction)

### Step 0: Configure

```bash
copy .env.example .env
```

Fill in at minimum `MONGODB_URI`, `AUTH_SECRET`, `BOOTSTRAP_OFFICER_EMAIL` and `BOOTSTRAP_OFFICER_PASSWORD`. Generate a signing secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The backend **refuses to start** if `MONGODB_URI` or `AUTH_SECRET` is missing, or if the secret is shorter than 32 characters. `.env` is gitignored — never commit it.

> MongoDB Atlas must allow the connecting machine's IP address. If start-up reports the database is unreachable, check the Atlas access list before anything else.

### Step 1: Start the Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

On start-up the backend will:

1. Ping MongoDB and abort if it is unreachable, so a request never fails later on a silent storage error.
2. Create the indexes the query patterns depend on.
3. Load the five scheme configurations, and seed the reference register on an empty database.
4. Create the officer account from the environment if it does not already exist.

- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- Health: `GET /health` returns `503` rather than a healthy body when the database is down.

On Windows, verify OCR with `tesseract --version`; if it is not on `PATH`, set `TESSERACT_CMD` to the full path. Install with `winget install --id UB-Mannheim.TesseractOCR --exact`.

### Step 2: Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The portal runs at `http://localhost:5173` and reads `VITE_API_URL` (default `http://localhost:8000`).

### Verifying the build

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests

cd ..\frontend
npm run build
```

The workflow tests run against a throwaway database named by `AROHAN_TEST_DB` (default `arohan_st_test`) and drop it afterwards, so the development database is never modified by the test suite. They need `MONGODB_URI` and `AUTH_SECRET` to be configured, but no `BOOTSTRAP_*` values.

---

## 🗄️ Data Model

| Collection | Holds |
|---|---|
| `users` | Accounts, bcrypt password hashes, role, activation state |
| `applicants` | Applicant profile linked one-to-one with a user |
| `schemes` | Scheme configuration: criteria, rules, form fields, required documents |
| `applications` | One record per submission, with its status, declared data and rule result |
| `documents` | Metadata per document; the bytes live in GridFS under `gridfs_id` |
| `audit_events` | Append-only workflow history per application |
| `notifications` | In-app messages for the applicant |
| `awards` | Sanctioned award lifecycle and amount |
| `payments` | Manual disbursement milestones, capped at the award amount |
| `counters` | Atomic id sequences, so ids stay stable and unique |

Document binaries are stored in the GridFS bucket `document_files` and are served **only** through `GET /private-documents/{id}/file`, which resolves the applicant who owns the application and rejects everyone else. Files are limited to 10 MB, checked by extension *and* by magic-byte signature, and are served as attachments with a hardened content type and `nosniff` header.

### Application lifecycle

```
SUBMITTED ──> UNDER_REVIEW ──> SELECTED ──> APPROVED
     │              │              │
     │              └──> NOT_SELECTED
     ├──> DEFICIENT ──> UNDER_REVIEW   (applicant corrects and re-submits)
     └──> WITHDRAWN                     (applicant withdraws while still open)
                        REJECTED
```

`APPROVED`, `REJECTED`, `SELECTED`, `NOT_SELECTED` and `WITHDRAWN` are all **locked**: documents cannot be changed, decisions cannot be altered, and an award requires a recorded `SELECTED` state first.

---

## Scheme Rules and Scope

Scheme forms and validation rules are stored in `backend/data/scheme_configs/*.json`, each with a `source_guideline` recording the guideline used to configure it. Internal codes are `NFST`, `NOS`, `TOP_CLASS`, `POST_MATRIC` and `PRE_MATRIC`; codes from the scheme inventory are preserved as `external_code`.

- **NFST**: ST category, 55% minimum PG marks, maximum age 36 as of 1 July, eligible research courses, regular/full-time mode, covered institution category. No income ceiling.
- **NOS**: ST category, ₹6 lakh income ceiling (orphan exception), course-specific maximum age (32/35/38), 55% marks unless admitted to a QS top-1,000 institution, one-child/one-award conditions and admission stage.
- **Top Class**: ST category, ₹6 lakh income ceiling (orphan exception), graduate/postgraduate course, notified institute/course, merit admission, no private management quota, no duplicate scholarship.
- **Post-Matric**: ST category, ₹2.5 lakh income ceiling (orphan exception), recognized course/institution, no concurrent scholarship, Top Class duplication check.
- **Pre-Matric**: ST category, ₹2.5 lakh income ceiling (orphan exception), eligible school/class, no concurrent scholarship, no repeat award for the same class.

These checks evaluate applicant **declarations** against the configured rules. They are not proof: institute lists, disability/PVTG evidence, certificates and admissions all still require an authorised officer to verify. The ranking desk sorts by a configured marks field as an advisory aid; it does not implement official quotas, category rosters, committee decisions, or scheme-specific merit rules. Confirm current amendments and State/UT rules before production use.

---

## 📡 REST API Reference

The scheme catalogue and health endpoints are public. Everything else requires the bearer token from `POST /auth/login`. Applicant routes only ever expose the signed-in applicant's own records; officer routes require the `admin` role.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create an applicant account and sign in |
| `POST` | `/auth/login` | Issue an expiring signed session (email + password) |
| `GET` | `/auth/me` | The signed-in account, including its applicant record |
| `GET` | `/auth/officer-check` | Whether an officer account exists |
| `GET` | `/schemes` | List all active schemes |
| `GET` | `/schemes/{id}` | Scheme criteria and dynamic form configuration |
| `GET` | `/schemes/code/{code}` | Scheme by code (`NFST`, `NOS`, `TOP_CLASS`, `POST_MATRIC`, `PRE_MATRIC`) |
| `POST` | `/applications` | Submit an application for the signed-in applicant |
| `POST` | `/applications/{id}/documents` | Upload a document to GridFS and extract its text (max 10 MB) |
| `GET` | `/applications/mine` | The signed-in applicant's applications |
| `GET` | `/applications/{id}` | An owned application, or any application for an officer |
| `PATCH` | `/applications/{id}` | Correct a deficient application and return it for review |
| `POST` | `/applications/{id}/withdraw` | Withdraw an application that is still open |
| `GET` | `/applications/notifications` | Applicant notifications |
| `POST` | `/applications/notifications/{id}/read` | Mark an owned notification as read |
| `GET` | `/applications/awards` | The applicant's approved awards |
| `GET` | `/admin/queue` | Paginated review queue — filter, search, sort |
| `POST` | `/admin/documents/{id}/verification` | Verify or mark a document deficient |
| `POST` | `/admin/applications/{id}/decision` | Record a reasoned selection/approval/deficiency/rejection |
| `GET` | `/admin/applications/{id}/audit` | Workflow audit history |
| `GET` | `/admin/selection` | Advisory marks-based ranking |
| `GET` | `/admin/dashboard` | Dashboard aggregates |
| `GET` | `/admin/report.csv` | CSV report (formula-injection safe) |
| `GET` | `/admin/awards` | Award and payment overview |
| `PUT` | `/admin/applications/{id}/award` | Update award lifecycle and sanction details |
| `POST` | `/admin/awards/{id}/payments` | Add a manual payment milestone |
| `GET` | `/private-documents/{id}/file` | Stream a document as its applicant or an officer |
| `GET` | `/health` | Service and database health |

### Not in scope

Notifications are in-app only. Email/SMS delivery, e-mail verification, government identity federation, official selection rosters and quotas, and treasury/DBT integration are not implemented. Do not treat this platform's controls as a production security certification.

---

## 📄 License

MIT License. Built for Smart India Hackathon (SIH).
