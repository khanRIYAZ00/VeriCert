# VeriCert 

VeriCert is a multi-tenant certificate platform that lets clubs create certificate templates, issue signed certificates for event participants, and let recipients verify authenticity via a QR code.

It’s built with:

- **Backend**: Python **FastAPI** + **SQLAlchemy** (SQLite by default)
- **Frontend**: **React** + **Vite**

The system is “multi-tenant” because clubs are isolated by authorization rules: users can only access the clubs they are members of.

---

## Architecture Overview

### 1) Clubs & Templates (Design-time)

Club admins can:

1. Upload a **certificate artwork** (PNG/JPG) or a **one-page PDF**.
2. Define **fields** (recipient name, credential id, issue date, etc.).
3. Drag and position fields on top of the artwork.
4. Save as a **draft** or **publish** a template.

Publishing locks the template so issuing certificates uses a stable layout.

### 2) Events (Where templates are used)

Admins create events and can associate each event with a **published template**.

### 3) Issuance (Run-time)

Admins can issue certificates in two ways:

- **Single**: manually enter recipient data.
- **Batch**: upload a CSV containing recipients.

For each issued certificate, the backend:

1. Builds a structured **credential JSON**.
2. Calculates a **SHA-256 hash** of the credential.
3. Signs the credential using **Ed25519**.
4. Renders a **final PDF certificate** by merging the artwork and overlay text fields.
5. Generates a QR code that points to the public verification endpoint.

### 4) Verification (Public)

Each certificate includes a QR code. Scanning it opens the `/verify/{credential_id}` endpoint, which:

- recomputes the hash from the stored credential,
- verifies the Ed25519 signature,
- returns whether the credential is valid.

---

## Project Layout

- `backend/`: FastAPI application (routes, auth, certificate rendering, signing)
- `frontend/`: React + Vite UI
- `storage/`: uploaded certificate artwork assets
- `keys/`: Ed25519 keypair used to sign credentials
- `generated/`: QR images produced during issuance

---

## Getting Started

### Requirements

- Python 3.10+
- Node.js 18+

---

## Run the Application (Development)

### 1) Start the backend (FastAPI)

From the repo root (`vericert/`):

```bash
python3 -m venv ./.venv
source ./.venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Backend listens at:

- `http://127.0.0.1:8000`

### 2) Start the frontend (React + Vite)

In a second terminal:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Frontend listens at:

- `http://127.0.0.1:5173`

---

## Application URLs

- Admin workspace (club management & issuing): `http://127.0.0.1:5173/`
- Student/recipient certificate portal: `http://127.0.0.1:5173/download`

The frontend calls the API at `http://127.0.0.1:8000`.

---

## Backend Configuration

The backend uses environment variables for:

### Database

- `VERICERT_DATABASE_URL`
  - Default: `sqlite:///./vericert.db`

### Auth token signing

- `VERICERT_TOKEN_SECRET`
  - Required; use a unique random value with at least 32 bytes of entropy.
  - Authentication startup fails if this is unset or too short.
- `VERICERT_ENV`
  - Use `production` when deployed. Production requires Redis-backed auth rate limits.
- `VERICERT_REDIS_URL`
  - Required in production; configure a private, authenticated Redis service.
  - Development without Redis uses a process-local limiter and logs a warning.
- `VERICERT_FRONTEND_URL`
  - Base URL used in password reset messages.

### Public verification QR base URL

- `VERICERT_PUBLIC_URL`
  - Optional (used to build QR links)
  - Default: `http://127.0.0.1:8000`

### SMTP (optional; enable email delivery on issuance)

If `VERICERT_SMTP_HOST` is set, the backend will:

- queue certificate delivery,
- send the rendered PDF via email.

Variables:

- `VERICERT_SMTP_HOST`
- `VERICERT_SMTP_PORT` (default: `587`)
- `VERICERT_SMTP_TLS` (default: `true`)
- `VERICERT_SMTP_USER`
- `VERICERT_SMTP_PASSWORD`
- `VERICERT_SMTP_FROM` (default: `certificates@vericert.local`)

You can copy and edit `.env.example`.

### Administrator and student accounts

There are no default administrator credentials. After configuring `.env`, create the
first platform administrator with:

```bash
python -m backend.admin_cli bootstrap
```

The command prompts for an administrator email and a password of at least 16
characters; it does not take passwords as command-line arguments or print them.
To recover an existing administrator account locally, use:

```bash
python -m backend.admin_cli set-password
```

Platform administrators can provision student accounts from the workspace. The
generated temporary password is returned once and requires a password change on
first sign-in. Students can change their password or request a single-use,
30-minute reset link sent to their registered email address. Configure SMTP to
enable password recovery.

Passwords use Argon2id (64 MiB memory, 3 iterations, parallelism 4). Tokens are
versioned and checked against current account state on every protected request;
password changes, resets, and account deactivation revoke existing tokens.
The application applies shared fixed-window limits through Redis in production.

---

## How the Certificate Flow Works

### 1) Template creation

Frontend uploads artwork via the `/clubs/{club_id}/templates` endpoint.

The backend saves the file under `storage/templates/` and stores:

- artwork key + mime type,
- page width/height,
- field definitions,
- and the layout overlay JSON.

### 2) Publish

When you publish, the backend:

- ensures at least one positioned field exists,
- flips template status to `published`,
- sets `published_at`.

### 3) Issuing

Issuing calls:

- `POST /issue` for single recipients
- `POST /issue/batch` for CSV uploads

The backend validates required fields against the template definition, creates an issuance record, renders a PDF certificate, and stores delivery state.

### 4) Download

Students sign in at `/download` (`POST /auth/login`), then list their own certificates with:

- `GET /certificates/download`

and download a PDF with:

- `GET /certificates/{issuance_id}/download`

Both routes require the student token. Certificates are matched to the signed-in user's roll number; admins may pass `?roll_no=` to look up another student.

Club admins can regenerate certificates too:

- `GET /issuances/{issuance_id}/certificate`

### 5) QR verification

Each QR encodes a link to:

- `/verify/{credential_id}`

That endpoint returns:

- `verified` (hash matches + signature verifies)
- the credential JSON

---

## Theme

The app uses a light/dark theme toggle (persisted in `localStorage` as `vericert-theme`). The first visit follows `prefers-color-scheme`.

---

## Security Notes (Practical)

- Admin/workspace API calls require auth (`Authorization: Bearer <token>`).
- Club access is enforced using `require_club_access`.
- Student downloads require authentication and only return certificates for that student's roll number.
  - Issuance regeneration requires club auth.

---

## Development Tips

- If frontend can’t connect: confirm the backend is running on port `8000`.
- If email delivery doesn’t work: set SMTP variables (or leave SMTP unconfigured to disable sending).
