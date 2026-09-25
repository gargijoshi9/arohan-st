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

The prototype combines a configurable, deterministic eligibility rule engine with applicant and officer interfaces. It flags declared-data mismatches and missing document entries for human review. It does not currently use ML/OCR, authenticate documents, or make final award decisions.

## Demo Login Credentials

- **Demo applicant:** Name `Ramesh Chandra Munda`, email `ramesh.munda@example.edu`. Applicant login uses name and email only; there is no applicant password in this demo.
- **MoTA officer (same ST Scholar Portal form):** Enter username/email `MotaOfficer@gmail.com`; the password field appears in that form. Password: `MotaOfficer`. The name field is optional for the officer.

These are prototype credentials and are not suitable for production deployment. Login checks are demo-only and are not backed by secure server-side identity/authentication.

---

## 📁 Exact Folder Structure

```
arohan-st/
├── backend/
│   ├── database.py                   # SQLite + SQLAlchemy configuration
│   ├── main.py                       # FastAPI application entrypoint & CORS
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
│   │   ├── admin.py                  # GET /admin/queue, POST /admin/applications/{id}/decision
│   │   └── documents.py              # Local document upload endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   └── rule_engine.py            # AI rule verification engine & mismatch detection
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
│               ├── ReviewQueue.tsx       # Queue sorted by confidence score
│               └── ApplicationDetail.tsx # Discrepancy highlights & action buttons
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

---

### Step 1: Start the Backend (FastAPI)

```bash
cd backend

# Create virtual environment (if not already created)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The backend starts at `http://localhost:8000`.
- Interactive API Docs (Swagger): `http://localhost:8000/docs`
- On startup, the database is automatically created (`arohan.db`) and pre-seeded with scheme configs and 4 realistic demo applications.

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

These checks only evaluate applicant declarations and document-upload entries. Current institute lists, disability/PVTG proof, certificates and admissions still need an authorized officer to verify. The PDFs describe merit lists, quotas and review committee decisions that are not automatic in this prototype. The two supplied `GuidelinesFellowshipandScholarship2022` PDFs are identical copies. The supplied scheme guidelines are implemented as given; confirm current amendments and State/UT rules before production use. OCR/document extraction is intentionally deferred.

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
   - Use the **Officer Adjudication Desk** to enter decision remarks and click **`Approve Fellowship Award`**, **`Request Resubmission (Deficient)`**, or **`Reject Application`**.
   - Status updates in real-time across both officer and applicant portals.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/schemes` | List all active fellowship and scholarship schemes |
| `GET` | `/schemes/{id}` | Get scheme criteria and dynamic form configuration |
| `GET` | `/schemes/code/{code}` | Get scheme by code (`NFST` or `NOS`) |
| `POST` | `/applications` | Submit application and trigger AI rule verification |
| `GET` | `/applications/{id}` | Get application status, declared data, and AI audit report |
| `GET` | `/applications/by-email/{email}` | List applications for an applicant email |
| `GET` | `/admin/queue` | List applications sorted by `confidence_score` or date |
| `POST` | `/admin/applications/{id}/decision` | Officer action (`APPROVE`, `REJECT`, `DEFICIENT`) |
| `POST` | `/documents/upload` | Store a PDF, image, or TXT document (maximum 10 MB) and return a view path |
| `GET` | `/uploads/{stored-file}` | View a stored uploaded document |
| `GET` | `/health` | Health check endpoint |

Uploaded files are stored under `backend/uploads/` and linked to submitted applications. The local demo server serves these files directly so applicants and officers can open them. This prototype does not authenticate document access; do not expose it to the public internet or use real sensitive documents until access controls are added.

---

## 📄 License
MIT License. Built for Smart India Hackathon (SIH) prototype demonstration.
