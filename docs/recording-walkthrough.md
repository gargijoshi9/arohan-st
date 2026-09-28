# AROHAN-ST — Recording Script: a Story, Not a Feature List

> **Do you need a real caste certificate? No.**
> The platform never verifies the *authenticity* of an upload. Upload checks only
> cover file size, extension and magic-byte signature; document verification is a
> human officer decision, and the rule engine only checks what the applicant
> *declared*. A real government-issued certificate would add nothing to the
> recording — and publishing a real document (even your own) is never a good idea.
>
> That is why `docs/sample-documents/` now contains **15 specimen certificate
> PDFs** (a `specimen_*.pdf` for every document type the five schemes require),
> each one watermarked **"SPECIMEN — NOT A REAL DOCUMENT"** so it can never be
> mistaken for a genuine record. Uploading `specimen_caste_cert.pdf` on camera
> renders as a full certificate in the browser and still extracts cleanly
> through the OCR pipeline (`ocr_status: SUCCESS`).

---

## The specimen files (in `docs/sample-documents/`)

| File | Backs the doc type | Used by schemes |
|---|---|---|
| `specimen_caste_cert.pdf` | ST certificate | all five |
| `specimen_income_cert.pdf` | Income certificate | NOS, Post-Matric, Pre-Matric, Top Class |
| `specimen_pg_marksheet.pdf` | PG marks | NFST |
| `specimen_qualifying_marks.pdf` | Qualifying marks | NOS |
| `specimen_marksheets.pdf` | Consolidated marks | Post-Matric, Top Class |
| `specimen_dob_proof.pdf` | 10th / DOB proof | NOS |
| `specimen_one_child_declaration.pdf` | One-child declaration | NOS |
| `specimen_admission_proof.pdf` | Foreign university offer | NOS |
| `specimen_admission_letter.pdf` | PhD admission letter | NFST |
| `specimen_institution_proof.pdf` | Institution category proof | NFST |
| `specimen_institution_course_proof.pdf` | Institution + course proof | Top Class |
| `specimen_domicile_cert.pdf` | Domicile certificate | Post-Matric, Pre-Matric |
| `specimen_school_enrolment.pdf` | School enrolment record | Pre-Matric |
| `specimen_bank_aadhaar.pdf` | Bank + Aadhaar linkage | Post-Matric, Pre-Matric, Top Class |
| `specimen_disability_cert.pdf` | Disability certificate | Pre-Matric |

Regenerate any of them with `python -m utils.specimen_documents` (run from
`backend/`). They are written to that folder and nowhere else.

---

## Before you press record

1. `cd backend`, activate the venv, and start the API. Let the start-up line
   print (schemes loaded, officer account created) before you switch windows.
2. In another terminal: `cd frontend && npm run dev`, then open
   `http://localhost:5173` and sign out.
3. Keep two extra tabs ready: `http://localhost:8000/docs` and
   `http://localhost:8000/health`.
4. The officer credentials are the `BOOTSTRAP_OFFICER_*` values in `.env`.
5. Drop the database and restart once, so the register is in its clean seeded
   state — the walkthrough below assumes untouched seeded data.

---

## The story

### Act 0 — "Every tribal scholar deserves a fair shot" (0:00–0:40)

Start *not with the software* but with the person.

> "Every year, thousands of Scheduled Tribe students apply for the Ministry of
> Tribal Affairs' scholarships — National Fellowship, National Overseas,
> Top Class, Post-Matric, and Pre-Matric. Five schemes, each with its own rules:
> income ceilings, age limits, mark thresholds, document lists. The problem has
> never been the money. It is that a single decision currently lives across
> paper files, PDFs, and email. AROHAN-ST is a single system where the whole
> story of an application - from the first upload to the final sanction - can be
> verified in one place."

Narrate as you do this:

> "The project is named for *arohan* — the climb. The scholar climbs; the system
> should never be the thing that stops them."

### Act 1 — "The machine underneath" (0:40–1:10)

Show the API terminal at rest.

> "The backend is FastAPI talking to MongoDB. Every record — accounts,
> applications, audits, awards, payments — is a document in the database. So are
> the uploaded certificates: they are stored in GridFS *inside* MongoDB, not in
> a folder on a server."

Open `/health` in the second tab.

> "Health is an honest endpoint. If the database were unreachable it would
> answer 503, not a cheerful success page — the machine refuses to pretend."

Briefly open `/docs`.

> "Twenty-eight endpoints across five routers: schemes, auth, applications,
> the officer desk, and private document streaming."

### Act 2 — "Nisha arrives" (1:10–1:45)

Sign out, and on the **Register** tab create the applicant.

> "This is Nisha Marandi, a research scholar. She registers herself — there is
> no shared code and no pre-provisioned list. The password is hashed with
> bcrypt; the server enforces its strength and refuses anything too weak, or a
> duplicate email."

Try the duplicate registration once and let the `409` show on screen.

> "A real account. The same email can never be created twice."

### Act 3 — "Nisha applies" (1:45–2:40)

Open **MoTA Schemes** and narrate across all five cards.

> "The scheme catalogue is not hardcoded in the app — it is generated from one
> JSON file per scheme: form fields, validation rules, required documents,
> stipend, tenure. Adding a new scheme means adding a JSON file, not rewriting
> software."

Pick NFST and fill the dynamic form. Tell the presenter's *you* to use values
that satisfy the rules: `category` ST, marks `68.5`, age `30`, course `Ph.D`,
`regular`/`full-time` study mode, a central/deemed university.

> "Answer honestly — the system will compare what you claim here with what the
> supporting documents actually say. The certificate number we enter is the one
> printed on the specimen certificate we are about to upload."

Submit *before* uploading anything.

> "Nisha submits incomplete — and the server catches it. The application comes
> back Deficient, because required documents are missing. It cannot be selected
> until an officer has verified every one."

Reopen the tracker, change the form, and re-submit for review.

> "Deficient is not a dead end. Nisha can correct her form and send it back for
> review — and the correction itself is recorded, so the officer sees what
> changed."

Now upload the star of the recording: **`specimen_caste_cert.pdf`**.
Open it with **View** so the browser renders the full certificate.

> "Watch where that file went. The browser is not reading a folder on the
> server — the certificate went into GridFS in MongoDB and is streamed back
> through a private route that only its owner and an officer can call."

Upload the other three NFST specimens — `specimen_pg_marksheet.pdf`,
`specimen_admission_letter.pdf`, `specimen_institution_proof.pdf` — then show
the document rows going from *uploaded* to *text extracted*.

> "Before a document is even worth looking at, the platform extracts its text —
> from a digital PDF this is direct text extraction, no OCR needed — and pulls
> out the fields an officer will compare against the claims."

Now **Track Status**: the timeline, the rule checks with their confidence
meters, and the notification bell.

> "Every stage is recorded. Every rule mismatch is named, not hidden."

### Act 4 — "Nisha hesitates" (2:40–2:50)

Show the withdrawal control but do not click it.

> "Life happens. While an application is still open — submitted, under review,
> or deficient — the applicant can withdraw it. The moment a decision is recorded,
> the file locks: no more changes, no more documents."

### Act 5 — "The officer's day" (2:50–3:40)

Click **Sign Out**, then sign in with the officer account.

> "Same form, different account — and the portal becomes the officer desk. The
> role was returned by the server, never guessed from the email address."

Open the **Verification Queue**: status cards, scheme filter, status filter,
search box, pagination.

> "This is a queue across every scheme, and all of it — filter, search, sort,
> page — runs in MongoDB. The numbers on the cards stay honest."

Search for Nisha's application and review it side by side.

> "Left, what Nisha declared. Right, what the extracted documents say. In the
> middle, the configured rules explaining an age check, an income check, a marks
> check — each outcome with a reason."

Mark the caste certificate **Verify** with a written reason, and watch an audit
event appear. Then reopen the audit history.

> "Every verification carries the officer's name and reasons. Nothing happens
> invisibly; an auditor can replay the whole day."

### Act 6 — "The decision" (3:40–4:25)

Now demonstrate the gate discipline — do it *on camera* as three attempts:

> "First, the honest mistakes — because the server refuses them."

1. Try **Approve** before selection. Refused.
2. Try **Select** with the documents still unverified. Refused.
3. Verify all four required documents with reasons, then try **Approve**
   while no selection is recorded. Refused.

> "Order is enforced in the backend, not by hiding buttons."

Now select, then approve, with reasons. Scroll the audit history.

> "Submission, four verifications, selection, approval — timestamped, signed,
> replayable."

### Act 7 — "The force multiplier" (4:25–5:00)

Open **Merit & Selection** (the ranking desk).

> "A marks-based ranking aid. It orders candidates for the available seats and
> states its ranking mode — but it never selects or rejects anyone. The human
> decision is always required and always recorded."

Open **Awards & Payments** — Nisha's freshly sanctioned award is here.

> "The approval created the award, locked to the sanctioned amount. Payments
> are recorded manually as milestones — and the system refuses to overpay."

Show a payment attempt above the cap being blocked. Then **Download CSV report**.

> "A per-scheme report, every row an application, reachable only with an
> officer's token."

### Act 8 — "Resolution" (5:00–5:25)

Sign back in as Nisha.

> "Now come home from the other side. Nisha signed in and found: a notification,
> a status that moved from submitted to approved, the award record, and the
> payment. No email needed — the record itself is the update."

Mark the notification read.

### Act 9 — Close (5:25–5:40)

> "That is the whole journey, in one system: self-registration, dynamic forms,
> GridFS document storage, honest rule checks, a private audit trail, an
> advisory ranking desk, and award milestones. And what it deliberately does
> *not* do: it does not claim to authenticate a document, apply official
> quotas, or move money. The specimens we just used are explicitly watermarked
> as training material. AROHAN-ST makes the officer's judgement *informed*,
> visible, and repeatable — it never replaces it."

---

## Showing the documents on camera

- **Upload a real-looking file**: during Act 3, drag `specimen_caste_cert.pdf`
  from `docs/sample-documents/` into the uploader. The document row then shows
  an extraction result; clicking **View** opens a new browser tab with the full
  certificate — pause here, zoom in, and let the watermark read
  "SPECIMEN — NOT A REAL DOCUMENT" on camera.
- **Show extraction, not just the file**: in the officer review (Act 5), point
  at the "extracted" column — "PDF text extraction" with the certificate number
  — and the declared value beside it. That contrast is the whole point.
- **Show a stored file streams, not reads**: reopen Nisha's documents directly
  from the review screen. Same private route (`/private-documents/{id}/file`),
  same browser render — GridFS, not a disk path.
- **Keep the seeded register as the safety net**: the seven seeded applicants
  already have every document in GridFS, so if a live upload fails mid-take,
  the officer acts can continue on a seeded record instead.

---

## If something goes wrong on camera

| Symptom | Recover |
|---|---|
| API won't start | "The service refuses to start rather than fail silently — that is the health check I keep talking about." Fix `.env`, restart. |
| Duplicate-email 409 on the *first* register | The register was re-seeded earlier. Use `verify.applicant@example.com` and claim it is a "different take". |
| Officer login rejected | Credentials are the `BOOTSTRAP_OFFICER_*` values. Do not change `.env` once the DB exists — update the stored account instead. |
| Upload rejected | "Extension and byte-signature must agree, and it must be under 10 MB." Use another specimen PDF. |
| Selection refused but everything looks right | A required document is still unverified or a rule is failing — that is the gate working. Verify every doc, then select. |
| Register is cluttered from earlier takes | Reset: drop the database, restart the API. The seeder rebuilds the whole register. |

## Seeded register (reference)

| Applicant | Scheme | State | Role in the recording |
|---|---|---|---|
| Ramesh Chandra Munda | NFST | APPROVED | Completed award + payment |
| Pooja Boro | NFST | UNDER_REVIEW | Parallel review example in the queue |
| Sunita Devi Soren | NOS | SUBMITTED | Six documents to verify |
| Amit Tirkey | NOS | DEFICIENT | Applicant correction & re-submission |
| Kiran Kumar Baiga | Pre-Matric | APPROVED | School-stage scheme |
| Deepak Nayak | Post-Matric | UNDER_REVIEW | Post-secondary scheme |
| Priya Kumari Deb | Top Class | SELECTED | Selection recorded, approval outstanding |

The **live story** (Nisha Marandi, registering for NFST on camera) is entirely
separate from the seeded register above. If a live take flubs, fall back to a
seeded record — every one already carries all of its documents in GridFS.
All seeded applicants share the password in `utils.seed.SEED_ACCOUNT_PASSWORD`.

## Feature coverage checklist (nothing left out)

| Feature | Where it appears in the story |
|---|---|
| Self-registration, bcrypt, password policy, duplicate detection | Act 2 |
| Server-decided roles on sign-in | Act 2 → Act 5 |
| Five-scheme catalogue, dynamic forms from JSON | Act 3 |
| Submit → Deficient when required docs missing | Act 3 |
| GridFS upload, magic-byte + size checks | Act 3 |
| PDF text extraction and field parsing | Act 3, Act 5 |
| Private document streaming, ownership enforced | Act 3, Act 5 |
| Status timeline + notifications | Act 3, Act 8 |
| Applicant withdrawal + status locking | Act 4 |
| Officer queue: filters, search, sort, pagination, cards | Act 5 |
| Document verification with reasons + audit trail | Act 5 |
| Deficient → correction → re-submission path | Act 3, Act 5 |
| Decision gate: select before approve, verified before select | Act 6 |
| Ranking desk (advisory, not decisions) | Act 7 |
| Award lifecycle + payment milestones under the cap | Act 7 |
| CSV report behind officer token | Act 7 |
| Dashboard aggregates | Act 5 (cards), Act 7 |
| Health / 503 behaviour, OpenAPI docs | Act 1 |
| All data in MongoDB + GridFS, no disk uploads | Act 1, Act 3 |