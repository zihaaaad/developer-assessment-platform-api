# Developer Assessment & Coding Platform API

A production-grade, asynchronous backend API built with Python, FastAPI, SQLAlchemy (Async), and Pydantic v2. The system evaluates candidate coding submissions against visible and hidden test cases in an isolated execution sandbox, calculates scores, and maintains real-time contest leaderboards.

---

## 1. Requirement Compliance Matrix (50 Marks)

| Evaluation Pillar | Marks | Implementation Details |
| :--- | :---: | :--- |
| **Authentication & Authorization** | **20** | - JWT Access Tokens (30m) & Refresh Tokens (7d) with token rotation.<br>- Password hashing using `bcrypt` (12 salt rounds).<br>- Role-Based Access Control (`ADMIN`, `RECRUITER`, `CANDIDATE`).<br>- Route protection guards (`require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])`).<br>- Cryptographic password reset workflow with time-limited tokens (15m expiry). |
| **Data Listing (Extended)** | **20** | - Multi-field search (`search=...`) across titles, slugs, and categories.<br>- Multi-condition filtering (`difficulty`, `category`, `status`, `created_after`, `created_before`).<br>- Configurable sorting (`sort_by=created_at|title|difficulty`, `sort_order=asc|desc`).<br>- Reusable pagination returning standardized metadata (`total_items`, `total_pages`, `current_page`, `page_size`, `has_next`, `has_prev`). |
| **CRUD & Schema Validation** | **10** | - Full CRUD operations across Users, Problems, Test Cases, Assessments, and Submissions.<br>- Strict Pydantic v2 request & response schema validation.<br>- Global exception handler with structured JSON responses. |

---

## 2. Sandboxed Code Execution & Security Design

### Execution Architecture
1. **Subprocess Isolation:** Candidate code is executed in temporary, isolated directories (`tempfile.mkdtemp`) which are destroyed immediately upon completion.
2. **Environment Variable Stripping:** All parent environment variables (including `JWT_SECRET_KEY` and database credentials) are removed before spawning the execution process.
3. **Time Limit Guard (TLE):** Strict execution timeout enforced via `asyncio.wait_for`. Runaway infinite loops (`while True: pass`) trigger immediate process termination (`kill()`) and return `TIME_LIMIT_EXCEEDED`.
4. **Memory Allocation Quota (MLE):** Configurable per-problem memory limits passed to runtimes (e.g. Node.js `--max-old-space-size`).
5. **Stdout Flood Guard:** Output buffer capped at 64 KB to prevent output flooding DoS attacks.
6. **Hidden Test Case Masking:** Candidate API responses mask hidden inputs and expected outputs, exposing only execution status and score weight.

---

## 3. Database Schema Overview

```text
 Users (id, name, email, password_hash, role, refresh_token, password_reset_token)
   │
   ├─► Assessments (id, recruiter_id, title, start_time, end_time, duration_minutes, status)
   │     │
   │     ├─► AssessmentProblems (assessment_id, problem_id, order_index, points)
   │     └─► AssessmentResults (assessment_id, candidate_id, total_score, problems_solved, rank)
   │
   └─► Submissions (id, candidate_id, problem_id, assessment_id, language, code, status, score, max_score)

 Problems (id, title, slug, difficulty, category, time_limit_ms, memory_limit_mb, is_published)
   │
   └─► TestCases (id, problem_id, input_data, expected_output, is_hidden, score_weight)
```

---

## 4. API Endpoints Reference

### Authentication & Profile (`/api/v1/auth`)
- `POST /api/v1/auth/signup` - Register a new account (`CANDIDATE` or `RECRUITER`)
- `POST /api/v1/auth/login` - Authenticate with email/password and obtain JWT tokens
- `POST /api/v1/auth/refresh-token` - Issue a fresh access token using a valid refresh token
- `POST /api/v1/auth/forgot-password` - Generate a time-limited password reset token
- `POST /api/v1/auth/reset-password` - Reset password using token
- `GET /api/v1/auth/me` - Get current authenticated user profile
- `PUT /api/v1/auth/me` - Update profile details or change password

### User Management (`/api/v1/users` - Admin Only)
- `GET /api/v1/users` - List all users with search, role filter, and pagination
- `PATCH /api/v1/users/{id}/role` - Update a user's role (`ADMIN`, `RECRUITER`, `CANDIDATE`)

### Coding Problems (`/api/v1/problems`)
- `POST /api/v1/problems` - Create a coding problem *(Recruiter/Admin)*
- `GET /api/v1/problems` - List problems with search, difficulty/category filters, sorting, and pagination
- `GET /api/v1/problems/{id_or_slug}` - Get problem details with visible sample test cases
- `PUT /api/v1/problems/{id}` - Update problem metadata *(Recruiter/Admin)*
- `DELETE /api/v1/problems/{id}` - Delete problem and cascade delete test cases *(Recruiter/Admin)*

### Test Cases (`/api/v1/problems/{id}/test-cases` & `/api/v1/test-cases/{id}`)
- `POST /api/v1/problems/{id}/test-cases` - Add a test case (marked visible or hidden) *(Recruiter/Admin)*
- `GET /api/v1/problems/{id}/test-cases` - List all test cases for a problem *(Recruiter/Admin)*
- `PUT /api/v1/test-cases/{id}` - Update test case *(Recruiter/Admin)*
- `DELETE /api/v1/test-cases/{id}` - Delete test case *(Recruiter/Admin)*

### Assessments & Contests (`/api/v1/assessments`)
- `POST /api/v1/assessments` - Create a timed assessment with assigned problems *(Recruiter/Admin)*
- `GET /api/v1/assessments` - List assessments with status filters and pagination
- `GET /api/v1/assessments/{id}` - Get assessment details and problems
- `PUT /api/v1/assessments/{id}` - Update assessment schedule *(Recruiter/Admin)*
- `POST /api/v1/assessments/{id}/problems` - Add problem link to assessment *(Recruiter/Admin)*
- `DELETE /api/v1/assessments/{id}/problems/{prob_id}` - Remove problem link *(Recruiter/Admin)*
- `GET /api/v1/assessments/{id}/plagiarism-report` - Generate AST & token similarity plagiarism report *(Recruiter/Admin)*
- `DELETE /api/v1/assessments/{id}` - Delete assessment *(Recruiter/Admin)*

### Code Submissions (`/api/v1/submissions`)
- `POST /api/v1/submissions/run-sample` - Dry run code against sample or custom input (No score recorded)
- `POST /api/v1/submissions` - Submit Python or JavaScript code for formal evaluation
- `GET /api/v1/submissions` - List submissions with filters (`problem_id`, `assessment_id`, `status`)
- `GET /api/v1/submissions/{id}` - Get detailed execution results and test case scores

### Leaderboards (`/api/v1/leaderboard`)
- `GET /api/v1/leaderboard/assessments/{assessment_id}` - Get real-time ranked leaderboard

---

## 5. Documentation Directory

- **[UNIVERSAL_SYSTEM_SPECIFICATION.md](UNIVERSAL_SYSTEM_SPECIFICATION.md):** Complete architecture design, entity relationship models, AST plagiarism engine mathematical formulation, cross-platform client integration protocols, and production deployment blueprints.
- **[FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md):** Client integration guide with TypeScript definitions, Axios token refresh interceptors, and UI state flows.

---

## 6. Quick Start & Setup

### Option A: Docker Compose (Recommended)
```bash
docker compose up -d --build
```
The server will be available at `http://localhost:8000`.

### Option B: Local Environment

#### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Node.js (for JavaScript code execution sandbox)

#### 2. Installation
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Run Automated Seeding & Verification
```bash
python seed_and_test.py
```

#### 4. Start Development Server
```bash
python run.py
```
The server will be running at `http://localhost:8000`.
- Swagger UI Documentation: `http://localhost:8000/docs`
- ReDoc Documentation: `http://localhost:8000/redoc`

---

## 7. Default Seed Credentials

| Role | Email | Password |
| :--- | :--- | :--- |
| **Admin** | `admin@assessment.com` | `Password123!` |
| **Recruiter** | `recruiter@assessment.com` | `Password123!` |
| **Candidate 1** | `alice@candidate.com` | `Password123!` |
| **Candidate 2** | `bob@candidate.com` | `Password123!` |

