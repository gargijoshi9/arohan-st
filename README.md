# AROHAN-ST (आरोहण-ST)
### Configurable Scholarship & Fellowship Management Platform for Scheduled Tribe (ST) Students
**MoTA schemes: NFST, NOS, Top Class, Post-Matric, and Pre-Matric**

---

## 🏛️ Overview

**AROHAN-ST** is a working prototype platform designed to streamline and accelerate the application, pre-screening, and adjudication process for higher education scholarships and fellowships offered to Scheduled Tribe students by the Ministry of Tribal Affairs (MoTA), Government of India:
1. **NFST**: National Fellowship for eligible ST research scholars in India.
2. **NOS**: National Overseas Scholarship for eligible ST students studying abroad.
3. **Top Class Education**: Scholarship for eligible ST students at Ministry-notified premier institutes.
4. **Post-Matric Scholarship**: Centrally Sponsored support for eligible recognized post-secondary courses.
5. **Pre-Matric Scholarship**: Centrally Sponsored support for eligible ST school students.

The prototype combines configurable eligibility checks, PDF/image OCR, applicant correction and tracking, and officer review. It includes signed demo sessions with role/ownership checks, private application-document access, decision/audit and notification records, an advisory marks-based ranking desk, scheme dashboard/CSV reporting, and award/payment milestone tracking. OCR, automated checks, and ranking are administrative aids only: they do not authenticate documents, establish entitlement, or make final award decisions.

## Demo Login Credentials

- **Demo applicant:** Name `Ramesh Chandra Munda`, email `ramesh.munda@example.edu`, demo verification code `123456`.
- **MoTA officer (same ST Scholar Portal form):** Enter username/email `MotaOfficer@gmail.com`; the password field appears in that form. Local default demo password: `MotaOfficer`. The name field is optional for the officer.

The backend validates login and issues an expiring signed session token; routes enforce applicant/officer roles and applicant ownership. The default applicant code is shared by design and the default officer password is public in this demo, so these are **not real identity verification or production credentials**. Set `AUTH_SECRET`, `DEMO_ADMIN_EMAIL`, `DEMO_ADMIN_PASSWORD`, and `DEMO_APPLICANT_OTP` in the backend process environment before running. Do not use real applicant information or expose the prototype publicly.

---

## 📁 Exact Folder Structure

```
arohan-st/
├── backend/
│   ├── database.py                   # SQLite + SQLAlchemy configuration
│   ├── main.py                       # FastAPI entrypoint, schema setup & CORS
│   ├── security.py                   # Signed demo bearer sessions and role checks
│   ├── requirements.txt              # Backend dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py                 # Scheme, Applicant, Application, Document tables
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py                # Pydantic request/response models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── schemes.py                # GET /schemes, GET /schemes/{id}
│   │   ├── applications.py           # POST /applications, GET /applications/{id}
│   │   ├── admin.py                  # Review, audit, ranking, dashboard, reports & awards
│   │   ├── auth.py                   # Demo login endpoint
│   │   └── private_documents.py      # Applicant-owned/officer-authorized file access
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rule_engine.py            # Configured eligibility checks
│   │   └── ocr_service.py            # PDF/image text extraction and document field parsing
│   ├── tests/
│   │   ├── test_ocr_service.py       # OCR profile and sample parsing tests
│   │   └── test_security.py          # Signed session and role guard tests
│   ├── utils/
│   │   ├── __init__.py
│   │   └── seed.py                   # Database seeder (schemes & realistic demo cases)
│   └── data/scheme_configs/
│       ├── nfst.json                 # NFST scheme criteria and form fields
│       ├── nos.json                  # NOS scheme criteria and form fields
│       ├── top_class.json            # Top Class scheme criteria and form
│       ├── post_matric.json          # Post-Matric scheme criteria and form
│       └── pre_matric.json           # Pre-Matric scheme criteria and form
├── frontend/
│   ├── index.html                    # Official portal page structure
│   ├── vite.config.ts                # Vite dev server configuration (port 5173)
│   ├── tailwind.config.js            # Govt portal theme (Navy #1e3a8a, Saffron #f97316)
│   └── src/
│       ├── main.tsx                  # React DOM mount with AuthProvider
│       ├── App.tsx                   # Main portal container & view switcher
│       ├── index.css                 # Tailwind base styles
│       ├── api/
│       │   ├── client.ts             # Fetch API wrapper
│       │   └── types.ts              # TypeScript interfaces
│       ├── hooks/
│       │   └── useAuth.tsx           # Demo applicant and officer login state
│       ├── components/
│       │   ├── Header.tsx            # MoTA portal masthead and login state
│       │   ├── Navbar.tsx            # Navigation tabs
│       │   ├── StatusBadge.tsx       # Color-coded status chip
│       │   └── ConfidenceMeter.tsx   # Rule-check indicator
│       └── pages/
│           ├── applicant/
│           │   ├── ApplicantLogin.tsx    # Student login & preset loader
│           │   ├── SchemeSelection.tsx   # Configured MoTA scheme catalogue
│           │   ├── ApplicationForm.tsx   # Dynamic scheme form & doc upload
│           │   └── StatusTracker.tsx     # Stage timeline & mismatch report
│           └── admin/
│               ├── ReviewQueue.tsx       # Review dashboard, reports and queue
│               ├── ApplicationDetail.tsx # Decision, documents and audit history
│               ├── SelectionDesk.tsx     # Advisory marks ranking and human review
│               └── AwardManagement.tsx   # Award lifecycle and payment milestones
└── docs/
    └── sample-documents/             # Sample verified certificate files for demo testing
        ├── st_caste_certificate_sample.txt
        ├── income_certificate_sample.txt
        ├── phd_admission_letter_sample.txt
        └── foreign_university_offer_sample.txt
```

---

## ⚙️ Quick Start (Running Locally)

### Prerequisites
- Python 3.9+
- Node.js 18+ and npm
- Tesseract OCR installed and available on PATH for scanned PDFs and images (digital PDFs and TXT files use local text extraction)

---

### Step 1: Start the Backend (FastAPI)

```bash
cd backend

# Create virtual environment (if not already created)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt

# Optional: use non-default demo secrets in this PowerShell session.
$bytes = New-Object byte[] 48
[System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
$env:AUTH_SECRET = [Convert]::ToBase64String($bytes)
$env:DEMO_ADMIN_EMAIL = "motaofficer@gmail.com"
$env:DEMO_ADMIN_PASSWORD = "MotaOfficer"
$env:DEMO_APPLICANT_OTP = "123456"

# Start the FastAPI server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The backend starts at `http://localhost:8000`.
- Interactive API Docs (Swagger): `http://localhost:8000/docs`
- On startup, the database is automatically created (`arohan.db`) and pre-seeded with scheme configs and realistic demo applications. Existing SQLite databases receive additive workflow-column migrations.
- On Windows, verify OCR installation with `tesseract --version`. If it is not on PATH, set `TESSERACT_CMD` to the full path to `tesseract.exe` before starting the backend.
- Windows install command: `winget install --id UB-Mannheim.TesseractOCR --exact`
- Tesseract uses English (`eng`) by default; set `TESSERACT_LANG` (for example, `eng+hin`) only after installing the corresponding trained language data.
- OCR is a preliminary aid: detected values and confidence are not proof of authenticity or eligibility. Unparsed or conflicting details remain for officer review.
- Applicant code and officer password above are local demonstration values. Real OTP delivery, applicant identity proofing and officer identity federation are not implemented.

Run the backend checks with `python -m unittest discover -s tests -v` from `backend/`, and the frontend type-check/build with `npm run build` from `frontend/`.

---

### Step 2: Start the Frontend (React + Vite + Tailwind)

In a separate terminal window:

```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend will run at `http://localhost:5173`.

---

## Scheme Rules and Scope

Scheme forms and validation rules are stored in `backend/data/scheme_configs/*.json`. Their `source_guideline` identifies the supplied guideline used to configure them. The internal codes are `NFST`, `NOS`, `TOP_CLASS`, `POST_MATRIC`, and `PRE_MATRIC`; the codes from the scheme inventory are preserved as `external_code` values.

- **NFST**: ST category, 55% minimum PG marks, maximum age 36 as of 1 July, eligible research courses, regular/full-time mode, and covered institution category. No income ceiling.
- **NOS**: ST category, ₹6 lakh income ceiling (orphan exception), course-specific maximum age (32/35/38), 55% marks unless admitted to a QS top-1,000 institution, one-child/one-award conditions and admission stage.
- **Top Class**: ST category, ₹6 lakh income ceiling (orphan exception), graduate/postgraduate course, notified institute/course, merit admission, no private management quota, and no duplicate scholarship.
- **Post-Matric**: ST category, ₹2.5 lakh income ceiling (orphan exception), recognized course/institution, no concurrent scholarship, and Top Class duplication check.
- **Pre-Matric**: ST category, ₹2.5 lakh income ceiling (orphan exception), eligible school/class, no concurrent scholarship, and no repeat award for the same class.

These checks only evaluate applicant declarations and document-upload entries. Current institute lists, disability/PVTG proof, certificates and admissions still need an authorized officer to verify. The ranking aid sorts by a configured marks field and basic checks; it does not implement official quotas, category rosters, committee decisions or real-time scheme-specific merit rules. The two supplied `GuidelinesFellowshipandScholarship2022` PDFs are identical copies. Confirm current amendments and State/UT rules before production use.

## 🚀 Live Demo Walkthrough (Hackathon Presentation Script)

Use the demo applicant and officer login credentials above to access the corresponding interfaces:

### Flow 1: High-Confidence Compliant Student (Ramesh Munda — NFST)
1. Sign in with the demo applicant's name and email above.
2. Open **Track Status**:
   - Shows Application `AROHAN-NFST-2024-81920` with status **`APPROVED`**.
   - The rule checks show no configured eligibility failures. Officers must still verify claims and documents.
   - Expand the application to view the 3-stage timeline, verified checks, and officer sanction note.

### Flow 2: Flagged Student (Amit Tirkey — NOS)
1. Sign in as the demo applicant and open **Track Status** to see their own applications.
2. The admin queue also includes a flagged NOS example with income and marks discrepancies for review.

### Flow 3: Submit a Fresh Application with Dynamic Fields
1. Switch to **MoTA Schemes** in the navigation bar.
2. Click **Apply for NFST** or **Apply for NOS**.
3. Observe how the form dynamically generates inputs and document requirements based on the scheme JSON config.
4. Complete the configured fields and upload documents as PDF, PNG, JPG/JPEG, or TXT files (up to 10 MB). Use **View** after upload to open the file; it is also available from applicant tracking and the admin review screen.
5. Click **Submit for Rule Checks** to create the record and open the status tracker.

### Flow 4: Adjudication Officer Queue
1. Enter the MoTA officer username and password in the ST Scholar Portal login form.
2. View the **Officer Adjudication Queue**:
   - Applications can be sorted using the stored rule-check indicator or submission date.
   - Filter by status (`Submitted`, `Under Review`, `Approved`, `Deficient`) or scheme.
   - Amit Tirkey's application is visibly highlighted in red (`Score 15%`).
3. Click **Review** on any application:
   - View side-by-side comparison of applicant declared parameters vs statutory scheme rules.
   - View rule discrepancies highlighted with exact error tags.
   - Use the **Officer Adjudication Desk** to enter a reason and record selection, not-selected, approval, deficiency, or rejection. Every action is recorded in the audit trail; decisions create applicant in-app notifications.
   - The **Merit & Selection** tab shows the configured-marks ranking aid and opens each application for human review. It does not apply statutory quotas or choose winners automatically.
   - The **Awards & Payments** tab records an approved award's lifecycle, dates, amount, and manual payment milestones. It does not transfer funds.
   - The applicant tracker supports detail corrections while deficient, secure document viewing, notifications, and award/payment status.
   - The dashboard includes per-scheme workflow counts and an authenticated CSV report.

---

## 📡 REST API Reference

All application, officer, award, notification, and private-document routes require a bearer session returned by `POST /auth/login`. Applicant routes only expose records belonging to the signed-in applicant. The scheme catalogue and health endpoints are public.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/login` | Issue an expiring signed demo session (applicant demo code or officer password) |
| `GET` | `/schemes` | List all active fellowship and scholarship schemes |
| `GET` | `/schemes/{id}` | Get scheme criteria and dynamic form configuration |
| `GET` | `/schemes/code/{code}` | Get scheme by code (`NFST` or `NOS`) |
| `POST` | `/applications` | Submit an application for the signed-in applicant |
| `POST` | `/applications/{id}/documents` | Upload and OCR an application document (maximum 10 MB) |
| `GET` | `/applications/mine` | List the signed-in applicant's applications |
| `GET` | `/applications/{id}` | Get an owned application or officer-authorized application detail |
| `PATCH` | `/applications/{id}` | Correct a deficient application and return it for officer review |
| `GET` | `/applications/notifications` | List applicant notifications |
| `POST` | `/applications/notifications/{id}/read` | Mark an owned notification as read |
| `GET` | `/applications/awards` | List the signed-in applicant's approved award records |
| `GET` | `/admin/queue` | Officer-only application review queue |
| `POST` | `/admin/applications/{id}/decision` | Record a reasoned officer selection/approval/deficiency/rejection |
| `GET` | `/admin/applications/{id}/audit` | View workflow audit history |
| `GET` | `/admin/selection` | Officer-only marks-based advisory ranking |
| `GET` | `/admin/dashboard` | Officer dashboard aggregates |
| `GET` | `/admin/report.csv` | Download officer-only CSV report |
| `GET` | `/admin/awards` | Officer award and payment overview |
| `PUT` | `/admin/applications/{id}/award` | Update award lifecycle and sanction tracking details |
| `POST` | `/admin/awards/{id}/payments` | Add a manual payment milestone |
| `GET` | `/private-documents/{id}/file` | Access a document only as its applicant or an officer |
| `GET` | `/health` | Health check endpoint |

Uploaded files are stored under `backend/uploads/` and are not served as a public static directory. Notifications are in-app only; email/SMS delivery, real applicant OTP identity verification, production officer identity federation, official selection rosters/quotas, and treasury/DBT integration remain outside this prototype. Use a unique strong `AUTH_SECRET` and non-demo credentials outside local demonstration, and do not treat this prototype's controls as a production security certification.

---

## 📄 License
MIT License. Built for Smart India Hackathon (SIH) prototype demonstration.
