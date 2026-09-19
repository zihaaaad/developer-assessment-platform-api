# Developer Assessment Platform API

A high-concurrency, asynchronous backend service built with Python 3, FastAPI, SQLAlchemy (Async), and Pydantic v2. The platform powers technical hiring assessments, algorithmic challenges, and competitive coding contests. It securely evaluates untrusted candidate code inside an isolated subprocess sandbox, grades against public and hidden test cases, computes real-time leaderboards, and flags code similarity using Abstract Syntax Tree (AST) analysis.

---

## Architectural Highlights

- **Asynchronous Core:** Non-blocking request handling powered by Python's `asyncio` event loop and SQLAlchemy AsyncEngine (`aiosqlite` for development, `asyncpg` for production).
- **Subprocess Execution Sandbox:** Ephemeral filesystem directories (`tempfile.mkdtemp`), stripped environment variables, CPU time limits (TLE), memory limits (MLE), and 64 KB stdout truncation to defend against resource exhaustion and fork attacks.
- **AST Plagiarism Engine:** Native Python AST tokenization and 4-gram Jaccard similarity index to detect algorithmic collusion across candidate submissions independent of variable renaming or code formatting.
- **Role-Based Access Control (RBAC):** Tiered permissions across `ADMIN`, `RECRUITER`, and `CANDIDATE` roles with JWT access and refresh token rotation, bcrypt password hashing, and cryptographic password reset workflows.

---

## Project Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── deps.py                  # Database session injection, JWT guards & RBAC
│   │   └── v1/
│   │       ├── api.py               # Main v1 router aggregator
│   │       └── endpoints/
│   │           ├── auth.py          # Signup, login, refresh token, password reset, profile
│   │           ├── users.py         # Admin user management and role updates
│   │           ├── problems.py      # Problem CRUD, search, filter, sort & pagination
│   │           ├── test_cases.py    # Public/hidden test case management
│   │           ├── assessments.py   # Timed contest creation & plagiarism report
│   │           ├── submissions.py   # Code execution, grading & dry-run tester
│   │           └── leaderboard.py   # Real-time ranked contest leaderboards
│   ├── core/
│   │   ├── config.py                # Pydantic Settings & environment variables
│   │   ├── security.py              # JWT token lifecycle, bcrypt hashing
│   │   └── exceptions.py            # Global custom exceptions & handlers
│   ├── db/
│   │   ├── base.py                  # SQLAlchemy declarative base
│   │   └── session.py               # Async engine & sessionmaker factory
│   ├── models/                      # SQLAlchemy ORM models & enums
│   ├── sandbox/
│   │   └── executor.py              # Subprocess execution sandbox (Python & JS)
│   ├── schemas/                     # Pydantic v2 validation & response models
│   ├── services/                    # Business logic & plagiarism detection engine
│   ├── utils/                       # Pagination, response helpers & slug generators
│   └── main.py                      # FastAPI application bootstrap & middleware
├── Dockerfile                       # Multi-runtime container (Python 3 + Node.js)
├── docker-compose.yml               # Container orchestration
├── seed_and_test.py                 # 11-step end-to-end automated verification suite
├── seed_rich_data.py                # Algorithmic problem & assessment data seeder
├── requirements.txt                 # Pinned dependencies
├── run.py                           # Development entrypoint
├── UNIVERSAL_SYSTEM_SPECIFICATION.md# Deep architectural & universal API specification
└── FRONTEND_INTEGRATION_GUIDE.md    # Frontend TypeScript interfaces & Axios setup
```

---

## Core Capabilities

### 1. Authentication & Security
- Cryptographic password hashing using `bcrypt` (12 salt rounds).
- Short-lived JWT access tokens (30 minutes) and long-lived refresh tokens (7 days) with token rotation.
- Secure password reset workflow utilizing time-limited, single-use reset tokens (15-minute expiry).
- Declarative route guards (`require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])`).

### 2. Problem Catalog & Test Suite Management
- Multi-field text search (`search=...`) across problem titles, slugs, and categories.
- Multi-condition filtering (`difficulty`, `category`, `is_published`, `created_at` date ranges).
- Dynamic sorting (`sort_by`, `sort_order`) and standardized pagination metadata (`total_items`, `total_pages`, `current_page`, `page_size`, `has_next`, `has_prev`).
- Support for public sample test cases and hidden evaluation test cases with custom score weights.
- Automatic server-side masking of hidden inputs and expected outputs on candidate requests.

### 3. Sandboxed Code Execution
- Multi-runtime support for **Python 3** and **JavaScript (Node.js)**.
- Ephemeral execution workspace with automatic teardown.
- Strict process execution timeout (TLE) via `asyncio.wait_for`.
- Output buffer cap (64 KB) to mitigate stdout flood denial-of-service.
- Ephemeral environment with parent environment variables stripped before spawning child processes.

### 4. Assessments & Real-Time Leaderboards
- Timed assessment creation with configurable duration, start time, and end time.
- Multiple problem links per assessment with custom point allocations.
- Real-time ranked leaderboards with deterministic tie-breaking based on submission timestamps.
- Automated AST-based code plagiarism reports calculating candidate-pair similarity scores.

---

## Getting Started

### Prerequisites
- Python 3.10 or higher (Tested on Python 3.14)
- Node.js (Required for JavaScript sandbox execution)

### Option 1: Local Environment Setup

1. **Create and activate a virtual environment:**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install project dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the automated verification suite:**
   ```bash
   python seed_and_test.py
   ```

4. **Seed rich algorithmic problems and sample assessments:**
   ```bash
   python seed_rich_data.py
   ```

5. **Start the development server:**
   ```bash
   python run.py
   ```
   The API will be available at `http://localhost:8000`.

### Option 2: Docker Compose

Run the entire service (including Python 3 and Node.js sandbox runtimes) inside a container:
```bash
docker compose up -d --build
```
Access the application at `http://localhost:8000`.

---

## Interactive API Documentation

Once the server is running, explore and test the endpoints directly via the interactive Swagger and ReDoc interfaces:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Default Seed Accounts

The seeding scripts populate the following test accounts:

| Role | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@assessment.com` | `Password123!` | System configuration, user management, full access |
| **Recruiter** | `recruiter@assessment.com` | `Password123!` | Problem authoring, assessment creation, plagiarism analysis |
| **Candidate 1** | `alice@candidate.com` | `Password123!` | Problem solving, code submissions, leaderboard viewing |
| **Candidate 2** | `bob@candidate.com` | `Password123!` | Problem solving, code submissions, leaderboard viewing |

---

## Environment Variables Reference

Configure environment settings in a `.env` file at the root of the backend directory:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `PROJECT_NAME` | string | `Developer Assessment Platform API` | Application name in OpenAPI docs |
| `ENVIRONMENT` | string | `development` | Runtime environment (`development`, `production`) |
| `DEBUG` | boolean | `true` | Debug mode toggle |
| `DATABASE_URL` | string | `sqlite+aiosqlite:///./dev.db` | Async database connection string |
| `JWT_SECRET_KEY` | string | `dev-secret-key-change-in-production...` | Secret key for signing JWT tokens |
| `JWT_ALGORITHM` | string | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `30` | Access token lifespan in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | `7` | Refresh token lifespan in days |
| `CORS_ORIGINS` | list | `["*"]` | Allowed CORS origins |
| `SANDBOX_TIMEOUT_SECONDS` | int | `5` | Maximum execution time before TLE |
| `SANDBOX_MAX_MEMORY_MB` | int | `128` | Maximum memory limit per process |
| `SANDBOX_MAX_OUTPUT_BYTES` | int | `65536` | Maximum stdout buffer size (64 KB) |

---

## Additional Technical Documentation

- **[UNIVERSAL_SYSTEM_SPECIFICATION.md](UNIVERSAL_SYSTEM_SPECIFICATION.md):** Detailed system architecture, entity-relationship diagrams, sandbox threat model, AST plagiarism mathematical formulation, and cross-platform integration contracts.
- **[FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md):** Frontend integration guide with TypeScript interfaces, Axios interceptors, and UI state flows.
