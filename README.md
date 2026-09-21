# AROHAN-ST (आरोहण-ST)
### AI-Enabled Scholarship & Fellowship Management Platform for Scheduled Tribe (ST) Students
**Ministry of Tribal Affairs (MoTA) Schemes: NFST & NOS**

---

## 🏛️ Overview

**AROHAN-ST** is a working prototype platform designed to streamline and accelerate the application, pre-screening, and adjudication process for higher education scholarships and fellowships offered to Scheduled Tribe students by the Ministry of Tribal Affairs (MoTA), Government of India:
1. **NFST (National Fellowship for Higher Education of ST Students)**: Supporting M.Phil and Ph.D doctoral research in Indian universities with monthly stipends.
2. **NOS (National Overseas Scholarship for ST Candidates)**: Supporting meritorious ST students pursuing Master's and Ph.D programs at prestigious overseas universities.

The platform combines a **lightweight, transparent AI rule engine** with a clean, official Indian government portal interface. It features automated eligibility checks, real-time discrepancy detection (e.g. income cap violations, minimum marks thresholds, category verification), a priority review queue for verification officers sorted by confidence score, and interactive status tracking for ST scholars.

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
│   │   └── admin.py                  # GET /admin/queue, POST /admin/applications/{id}/decision
│   ├── services/
│   │   ├── __init__.py
│   │   └── rule_engine.py            # AI rule verification engine & mismatch detection
│   ├── utils/
│   │   ├── __init__.py
│   │   └── seed.py                   # Database seeder (schemes & realistic demo cases)
│   └── data/scheme_configs/
│       ├── nfst.json                 # NFST scheme criteria, caps, and dynamic form fields
│       └── nos.json                  # NOS scheme criteria, caps, and dynamic form fields
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
│       │   └── useAuth.tsx           # Mock auth context & 1-click persona switcher
│       ├── components/
│       │   ├── Header.tsx            # MoTA portal masthead & demo switcher
│       │   ├── Navbar.tsx            # Navigation tabs
│       │   ├── StatusBadge.tsx       # Color-coded status chip
│       │   └── ConfidenceMeter.tsx   # AI confidence score gauge
│       └── pages/
│           ├── applicant/
│           │   ├── ApplicantLogin.tsx    # Student login & preset loader
│           │   ├── SchemeSelection.tsx   # Scheme cards (NFST & NOS)
│           │   ├── ApplicationForm.tsx   # Dynamic scheme form & doc upload
│           │   └── StatusTracker.tsx     # Stage timeline & mismatch report
│           └── admin/
│               ├── AdminLogin.tsx        # Verification officer access
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

## 🤖 AI Rule Engine Capabilities

The rule engine (`backend/services/rule_engine.py`) reads the declarative JSON configuration for each scheme and performs automated checks:

| Statutory Rule | NFST | NOS | Rule Engine Action |
|---|---|---|---|
| **Social Category** | ST (Scheduled Tribe) | ST (Scheduled Tribe) | Mismatch flagged if non-ST (`-35%` confidence) |
| **ST Certificate** | Valid Registration ID | Valid Registration ID | Warning flagged if absent/invalid (`-10%` confidence) |
| **Annual Family Income** | $\le$ ₹6,00,000 / annum | $\le$ ₹6,00,000 / annum | Hard error if declared income exceeds cap (`-30%` confidence) |
| **Academic Marks** | $\ge$ 55.0% in Master's | $\ge$ 60.0% in Qualifying Degree | Hard error if percentage is below threshold (`-25%` confidence) |
| **Applicant Age Limit** | No statutory age cap | $\le$ 35 years | Hard error if age exceeds 35 years (`-20%` confidence) |
| **Admission Status** | Full-time M.Phil / Ph.D | Unconditional offer from foreign university | Hard error if offer is conditional (`-20%` confidence) |
| **Required Proofs** | 5 mandatory documents | 5 mandatory documents | Warning flagged per missing document (`-8%` confidence) |

---

## 🚀 Live Demo Walkthrough (Hackathon Presentation Script)

Use the top dark **Hackathon Demo Switcher** bar to easily present all features:

### Flow 1: High-Confidence Compliant Student (Ramesh Munda — NFST)
1. Click **`Applicant 1: Ramesh (NFST - Pass)`** on the top bar.
2. View **Track Status**:
   - Shows Application `AROHAN-NFST-2024-81920` with status **`APPROVED`**.
   - AI Confidence Score is **98.0% (High Confidence)**.
   - Expand the application to view the 3-stage timeline, verified checks, and officer sanction note.

### Flow 2: Ineligible / Flagged Student (Amit Tirkey — NOS Discrepancies)
1. Click **`Applicant 2: Amit (NOS - Flagged)`** on the top bar.
2. View **Track Status**:
   - Shows Application `AROHAN-NOS-2024-19403` with status **`DEFICIENT (Resubmit)`**.
   - AI Confidence Score drops to **15.0% (Flagged Discrepancy)**.
   - Highlights the exact reasons in red:
     - Declared family income of **₹7,80,000 exceeds ₹6,00,000 cap**.
     - Qualifying degree marks of **54.5% is below minimum 60.0%**.
     - Conditional offer status instead of unconditional admission.

### Flow 3: Submit a Fresh Application with Dynamic Fields
1. Switch to **MoTA Schemes** in the navigation bar.
2. Click **Apply for NFST** or **Apply for NOS**.
3. Observe how the form dynamically generates inputs and document requirements based on the scheme JSON config.
4. Use the demo helper buttons:
   - **`Fill 100% Compliant Data`** to submit a passing application.
   - **`Fill Discrepant Data`** to test triggering rule engine flags.
5. Click **Submit & Run AI Verification** — instantaneously creates the record, runs the rule check, and opens the live status tracker.

### Flow 4: Adjudication Officer Queue (Dr. Arjun K. Meena)
1. Click **`Admin: MoTA Officer`** on the top bar.
2. View the **Officer Adjudication Queue**:
   - Applications sorted by AI confidence score.
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
| `GET` | `/health` | Health check endpoint |

---

## 📄 License
MIT License. Built for Smart India Hackathon (SIH) prototype demonstration.