# Universal System Specification & Architecture Manual

## 1. Executive Summary and Architecture Paradigm

The Developer Assessment & Coding Platform is an asynchronous backend system designed for automated programming assessments, competitive coding contests, and recruitment evaluations. It executes un-trusted candidate code across multiple programming languages within an isolated sandbox environment, matches execution outputs against public and hidden test suites, computes weighted scores, and maintains real-time contest leaderboards with integrated AST-based plagiarism detection.

### Architectural Principles
- **Asynchronous Non-Blocking I/O:** Built on Python's `asyncio` event loop using FastAPI and SQLAlchemy AsyncEngine (`aiosqlite` / `asyncpg`), ensuring high throughput under concurrent submission loads without thread starvation.
- **Micro-Modular Architecture:** Clean separation of concerns between API routing, dependency injection guards, service-layer orchestration, sandboxed process execution, and data access layers.
- **Zero-Trust Code Execution:** User-submitted code is treated as malicious by default and executed in isolated ephemeral subdirectories with stripped environment variables, strict timeouts, memory constraints, and output buffer caps.
- **Universal Client Compatibility:** Standardized RESTful JSON contracts, consistent error envelopes, deterministic pagination metadata, and standards-compliant JWT bearer authorization allow seamless integration with Web, Mobile (iOS/Android/Flutter), Desktop, and CI/CD clients.

---

## 2. System Architecture

### Component Hierarchy

```mermaid
flowchart TD
    Client["Client Layer (Web / Mobile / CLI)"]
    Gateway["Reverse Proxy / Ingress (Nginx / Cloud Load Balancer)"]
    FastAPIApp["FastAPI Core Engine"]
    
    subgraph CorePlatform ["Backend Services Layer"]
        AuthModule["Auth & RBAC Module (JWT / BCrypt)"]
        ProblemModule["Problem & Test Case Service"]
        AssessmentModule["Assessment Orchestrator"]
        SubmissionModule["Submission Pipeline"]
        PlagiarismModule["AST Plagiarism Engine"]
        LeaderboardModule["Leaderboard Ranker"]
    end
    
    subgraph ExecutionLayer ["Sandbox Isolation Layer"]
        ProcessSpawner["Process Spawner (asyncio.subprocess)"]
        PythonRuntime["Python 3 Isolated Worker"]
        NodeRuntime["Node.js Isolated Worker"]
        ResourceWatcher["Resource Watcher (TLE / MLE / Buffers)"]
    end
    
    subgraph DataLayer ["Persistence Layer"]
        RelationalDB[("SQL Database (SQLite / PostgreSQL)")]
    end
    
    Client --> Gateway
    Gateway --> FastAPIApp
    FastAPIApp --> AuthModule
    FastAPIApp --> ProblemModule
    FastAPIApp --> AssessmentModule
    FastAPIApp --> SubmissionModule
    FastAPIApp --> LeaderboardModule
    
    SubmissionModule --> ProcessSpawner
    AssessmentModule --> PlagiarismModule
    
    ProcessSpawner --> PythonRuntime
    ProcessSpawner --> NodeRuntime
    ProcessSpawner --> ResourceWatcher
    
    AuthModule --> RelationalDB
    ProblemModule --> RelationalDB
    AssessmentModule --> RelationalDB
    SubmissionModule --> RelationalDB
    LeaderboardModule --> RelationalDB
    PlagiarismModule --> RelationalDB
```

---

## 3. Domain Model and Persistence Design

### Entity Relationship Model

```mermaid
erDiagram
    USERS ||--o{ ASSESSMENTS : "creates"
    USERS ||--o{ SUBMISSIONS : "submits"
    USERS ||--o{ ASSESSMENT_RESULTS : "achieves"
    
    PROBLEMS ||--o{ TEST_CASES : "contains"
    PROBLEMS ||--o{ ASSESSMENT_PROBLEMS : "included_in"
    PROBLEMS ||--o{ SUBMISSIONS : "evaluated_against"
    
    ASSESSMENTS ||--o{ ASSESSMENT_PROBLEMS : "contains"
    ASSESSMENTS ||--o{ ASSESSMENT_RESULTS : "produces"
    ASSESSMENTS ||--o{ SUBMISSIONS : "tracks"
    
    USERS {
        int id PK
        string email UK
        string password_hash
        string name
        enum role "ADMIN, RECRUITER, CANDIDATE"
        string refresh_token
        string password_reset_token
        datetime password_reset_expires_at
        datetime created_at
        datetime updated_at
    }
    
    PROBLEMS {
        int id PK
        string title
        string slug UK
        text description
        enum difficulty "EASY, MEDIUM, HARD"
        string category
        int time_limit_ms
        int memory_limit_mb
        boolean is_published
        datetime created_at
        datetime updated_at
    }
    
    TEST_CASES {
        int id PK
        int problem_id FK
        text input_data
        text expected_output
        boolean is_hidden
        float score_weight
        datetime created_at
    }
    
    ASSESSMENTS {
        int id PK
        int recruiter_id FK
        string title
        text description
        datetime start_time
        datetime end_time
        int duration_minutes
        enum status "DRAFT, SCHEDULED, ACTIVE, COMPLETED, ARCHIVED"
        datetime created_at
        datetime updated_at
    }
    
    ASSESSMENT_PROBLEMS {
        int id PK
        int assessment_id FK
        int problem_id FK
        int order_index
        float points
    }
    
    SUBMISSIONS {
        int id PK
        int candidate_id FK
        int problem_id FK
        int assessment_id FK
        enum language "PYTHON, JAVASCRIPT"
        text code
        enum status "PENDING, EVALUATING, ACCEPTED, WRONG_ANSWER, TIME_LIMIT_EXCEEDED, MEMORY_LIMIT_EXCEEDED, RUNTIME_ERROR, COMPILATION_ERROR"
        float score
        float max_score
        float execution_time_ms
        float memory_used_mb
        json test_case_results
        datetime created_at
    }
    
    ASSESSMENT_RESULTS {
        int id PK
        int assessment_id FK
        int candidate_id FK
        float total_score
        int problems_solved
        int rank
        datetime completed_at
    }
```

### State Transition Lifecycles

#### Submission State Machine
1. `PENDING`: Submission record written to database with initial parameters.
2. `EVALUATING`: Worker allocates execution directory and initiates sandbox subprocess.
3. Final States:
   - `ACCEPTED`: Code executed successfully on all test cases with exact output match.
   - `WRONG_ANSWER`: Code exited cleanly with code 0, but stdout diverged from expected output.
   - `TIME_LIMIT_EXCEEDED`: Process exceeded problem's configured runtime budget and was terminated.
   - `MEMORY_LIMIT_EXCEEDED`: Process exceeded allocated memory quota.
   - `RUNTIME_ERROR`: Process crashed with non-zero exit code or uncaught exception.

#### Assessment State Machine
1. `DRAFT`: Recruiter configuring title, duration, and problem set. Visible only to author and admins.
2. `SCHEDULED`: Finalized assessment waiting for `start_time` window to open.
3. `ACTIVE`: Current time is between `start_time` and `end_time`. Candidates can start and submit code.
4. `COMPLETED`: Assessment window closed. Submission disabled; final leaderboard and plagiarism reports computed.
5. `ARCHIVED`: Read-only historic record.

---

## 4. Sandboxed Code Execution Subsystem

### Isolation Matrix
- **Filesystem Isolation:** Each execution creates a randomized directory via `tempfile.mkdtemp(prefix="exec_")`. The source file is written, executed, and the entire directory tree is recursively deleted in a `finally` block.
- **Environment Sanitization:** Parent process environment (`os.environ`) containing database credentials, JWT secrets, and system paths is cleared. A minimal environment containing only essential runtime variables (`PATH`, `LANG=en_US.UTF-8`) is injected.
- **Execution Time Bounds (TLE):** Async execution is wrapped in `asyncio.wait_for(timeout=limit_seconds)`. If execution exceeds the limit, `process.kill()` sends `SIGKILL` to the child process immediately, preventing runaway compute cycles or fork abuse.
- **Output Flooding Mitigation (OLE):** Process stdout and stderr read buffers are capped at 64 KB (`65,536 bytes`). Submissions attempting to flood the output buffer are truncated immediately to protect API throughput and persistence layer storage.
- **Language Configurations:**
  - **Python 3:** Executed as `python -u source.py` with standard I/O pipes.
  - **JavaScript:** Executed via Node.js with `--max-old-space-size=<MB>` memory limit flags.

---

## 5. Anti-Cheat and Plagiarism Detection Engine

The plagiarism engine evaluates lexical and structural similarity between candidate submissions for a shared assessment problem without relying on external cloud APIs.

```mermaid
flowchart LR
    Code1["Candidate Code A"] --> AST1["Python AST Parser"]
    Code2["Candidate Code B"] --> AST2["Python AST Parser"]
    
    AST1 --> Tokens1["Structural Token Sequence A"]
    AST2 --> Tokens2["Structural Token Sequence B"]
    
    Tokens1 --> Ngram1["4-gram Feature Set A"]
    Tokens2 --> Ngram2["4-gram Feature Set B"]
    
    Ngram1 --> Jaccard["Jaccard Similarity Engine"]
    Ngram2 --> Jaccard
    
    Jaccard --> Score["Similarity Score: |A ∩ B| / |A ∪ B|"]
```

### Mathematical Model
1. **Token Extraction:** For Python submissions, the source code is parsed into an Abstract Syntax Tree (AST) using Python's native `ast` module. Variable names and docstrings are normalized, retaining node sequence semantics (`FunctionDef`, `For`, `If`, `BinOp`, `Compare`, `Return`).
2. **N-gram Generation:** The linear token sequence is transformed into overlapping contiguous n-grams of degree $N = 4$.
3. **Jaccard Similarity Index:**
   $$\text{Similarity}(S_1, S_2) = \frac{|S_1 \cap S_2|}{|S_1 \cup S_2|}$$
4. **Fallback Mechanism:** For non-AST or multi-language inputs, normalized token-stream decomposition extracts alphanumeric lexemes stripped of comments and whitespace.
5. **Report Generation:** Comparisons yielding a similarity index $\ge 0.70$ (70%) are flagged as high-risk, identifying matching candidate pairs, submission identifiers, and similarity percentages.

---

## 6. Universal API Communication Protocol

### Base URL and Headers
- **Development Base URL:** `http://localhost:8000/api/v1`
- **Production Base URL:** `https://api.yourdomain.com/api/v1`
- **Standard Headers:**
  - `Content-Type: application/json`
  - `Authorization: Bearer <ACCESS_TOKEN>` (for authenticated endpoints)

### Standard Success Envelope (Data Listing & Pagination)
```json
{
  "items": [
    { "id": 1, "title": "Two Sum", "difficulty": "EASY" }
  ],
  "total_items": 1,
  "total_pages": 1,
  "current_page": 1,
  "page_size": 20,
  "has_next": false,
  "has_prev": false
}
```

### Universal Error Envelope Format
All error responses return standard HTTP error status codes with a consistent JSON body:
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Problem with ID 42 was not found.",
    "details": null
  }
}
```

#### Standard Error Codes Matrix
| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| `400` | `VALIDATION_ERROR` | Malformed request body or invalid parameters |
| `401` | `AUTHENTICATION_ERROR` | Missing, invalid, or expired JWT access token |
| `403` | `PERMISSION_DENIED` | Insufficient role permissions for the target resource |
| `404` | `RESOURCE_NOT_FOUND` | Target entity does not exist |
| `409` | `RESOURCE_CONFLICT` | Unique constraint conflict (e.g. duplicate email or slug) |
| `422` | `UNPROCESSABLE_ENTITY` | Pydantic type validation failure |
| `500` | `INTERNAL_SERVER_ERROR` | Unhandled server exception |

---

## 7. Complete API Endpoint Catalog

### Authentication & User Profile (`/api/v1/auth`)

#### 1. Register User
- **Method / Route:** `POST /api/v1/auth/signup`
- **Access:** Public
- **Request Body:**
```json
{
  "email": "candidate@example.com",
  "password": "SecurePassword123!",
  "name": "Jane Doe",
  "role": "CANDIDATE"
}
```
- **Response (`201 Created`):**
```json
{
  "user": {
    "id": 1,
    "email": "candidate@example.com",
    "name": "Jane Doe",
    "role": "CANDIDATE",
    "created_at": "2026-09-19T10:00:00Z",
    "updated_at": "2026-09-19T10:00:00Z"
  },
  "tokens": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

#### 2. Authenticate (Login)
- **Method / Route:** `POST /api/v1/auth/login`
- **Access:** Public
- **Request Body:**
```json
{
  "email": "candidate@example.com",
  "password": "SecurePassword123!"
}
```
- **Response (`200 OK`):** Same schema as Signup response.

#### 3. Refresh Access Token
- **Method / Route:** `POST /api/v1/auth/refresh-token`
- **Access:** Public (Requires valid Refresh Token)
- **Request Body:**
```json
{
  "refresh_token": "eyJhbGciOi..."
}
```
- **Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### 4. Forgot Password Request
- **Method / Route:** `POST /api/v1/auth/forgot-password`
- **Access:** Public
- **Request Body:**
```json
{
  "email": "candidate@example.com"
}
```
- **Response (`200 OK`):**
```json
{
  "message": "If this email exists in our system, a password reset token has been generated.",
  "reset_token": "a1b2c3d4e5f6..."
}
```

#### 5. Confirm Password Reset
- **Method / Route:** `POST /api/v1/auth/reset-password`
- **Access:** Public
- **Request Body:**
```json
{
  "token": "a1b2c3d4e5f6...",
  "new_password": "NewSecurePassword456!"
}
```
- **Response (`200 OK`):**
```json
{
  "message": "Password has been successfully reset. Please log in with your new credentials."
}
```

#### 6. Read Current Profile
- **Method / Route:** `GET /api/v1/auth/me`
- **Access:** Authenticated (`ADMIN`, `RECRUITER`, `CANDIDATE`)
- **Response (`200 OK`):**
```json
{
  "id": 1,
  "email": "candidate@example.com",
  "name": "Jane Doe",
  "role": "CANDIDATE",
  "created_at": "2026-09-19T10:00:00Z",
  "updated_at": "2026-09-19T10:00:00Z"
}
```

#### 7. Update Profile Details or Password
- **Method / Route:** `PUT /api/v1/auth/me`
- **Access:** Authenticated
- **Request Body:**
```json
{
  "name": "Jane Doe Updated",
  "current_password": "SecurePassword123!",
  "new_password": "NewPassword789!"
}
```
- **Response (`200 OK`):** Updated user object.

---

### User Administration (`/api/v1/users`)

#### 1. List Users
- **Method / Route:** `GET /api/v1/users`
- **Access:** `ADMIN`
- **Query Parameters:**
  - `search` (string, optional): Matches against email or name.
  - `role` (string, optional): Filter by `ADMIN`, `RECRUITER`, `CANDIDATE`.
  - `page` (integer, default: 1): Page index.
  - `page_size` (integer, default: 20): Items per page.
- **Response (`200 OK`):** Paginated User list.

#### 2. Update User Role
- **Method / Route:** `PATCH /api/v1/users/{user_id}/role`
- **Access:** `ADMIN`
- **Request Body:**
```json
{
  "role": "RECRUITER"
}
```
- **Response (`200 OK`):** Updated user profile.

---

### Problem Management (`/api/v1/problems`)

#### 1. Create Problem
- **Method / Route:** `POST /api/v1/problems`
- **Access:** `ADMIN`, `RECRUITER`
- **Request Body:**
```json
{
  "title": "Reverse Linked List",
  "slug": "reverse-linked-list",
  "description": "Given the head of a singly linked list, reverse the list and return its head.",
  "difficulty": "EASY",
  "category": "Data Structures",
  "time_limit_ms": 2000,
  "memory_limit_mb": 128,
  "is_published": true
}
```
- **Response (`201 Created`):** Created Problem object.

#### 2. List Problems
- **Method / Route:** `GET /api/v1/problems`
- **Access:** Public (Draft problems visible only to `ADMIN` and `RECRUITER`)
- **Query Parameters:**
  - `search` (string, optional): Full-text search across title and category.
  - `difficulty` (string, optional): `EASY`, `MEDIUM`, `HARD`.
  - `category` (string, optional): Filter by domain category.
  - `is_published` (boolean, optional): Filter publication state.
  - `sort_by` (string, default: `created_at`): `created_at`, `title`, `difficulty`.
  - `sort_order` (string, default: `desc`): `asc`, `desc`.
  - `page` (integer, default: 1)
  - `page_size` (integer, default: 20)
- **Response (`200 OK`):** Paginated Problem list.

#### 3. Get Problem Details
- **Method / Route:** `GET /api/v1/problems/{id_or_slug}`
- **Access:** Public
- **Response (`200 OK`):** Problem object including all public sample test cases. Hidden test cases are omitted for candidate requests.

#### 4. Update Problem
- **Method / Route:** `PUT /api/v1/problems/{problem_id}`
- **Access:** `ADMIN`, `RECRUITER`
- **Request Body:** Problem metadata fields to update.
- **Response (`200 OK`):** Updated Problem object.

#### 5. Delete Problem
- **Method / Route:** `DELETE /api/v1/problems/{problem_id}`
- **Access:** `ADMIN`, `RECRUITER`
- **Response (`200 OK`):** `{"message": "Problem deleted successfully."}`

---

### Test Case Management (`/api/v1/problems/{problem_id}/test-cases` & `/api/v1/test-cases/{id}`)

#### 1. Add Test Case to Problem
- **Method / Route:** `POST /api/v1/problems/{problem_id}/test-cases`
- **Access:** `ADMIN`, `RECRUITER`
- **Request Body:**
```json
{
  "input_data": "[1, 2, 3, 4, 5]",
  "expected_output": "[5, 4, 3, 2, 1]",
  "is_hidden": true,
  "score_weight": 25.0
}
```
- **Response (`201 Created`):** Created Test Case object.

#### 2. List Problem Test Cases
- **Method / Route:** `GET /api/v1/problems/{problem_id}/test-cases`
- **Access:** `ADMIN`, `RECRUITER`
- **Response (`200 OK`):** Array of all test cases (both public and hidden).

#### 3. Update Test Case
- **Method / Route:** `PUT /api/v1/test-cases/{test_case_id}`
- **Access:** `ADMIN`, `RECRUITER`
- **Request Body:** Updated input, expected output, hidden flag, or score weight.
- **Response (`200 OK`):** Updated Test Case object.

#### 4. Delete Test Case
- **Method / Route:** `DELETE /api/v1/test-cases/{test_case_id}`
- **Access:** `ADMIN`, `RECRUITER`
- **Response (`200 OK`):** `{"message": "Test case deleted successfully."}`

---

### Assessment & Contest Management (`/api/v1/assessments`)

#### 1. Create Assessment
- **Method / Route:** `POST /api/v1/assessments`
- **Access:** `ADMIN`, `RECRUITER`
- **Request Body:**
```json
{
  "title": "Backend Engineering Screening - Q3",
  "description": "Evaluate asynchronous programming and algorithmic efficiency.",
  "start_time": "2026-09-20T09:00:00Z",
  "end_time": "2026-09-20T12:00:00Z",
  "duration_minutes": 90,
  "status": "SCHEDULED",
  "problem_links": [
    { "problem_id": 1, "order_index": 1, "points": 50.0 },
    { "problem_id": 2, "order_index": 2, "points": 50.0 }
  ]
}
```
- **Response (`201 Created`):** Created Assessment object with linked problems.

#### 2. List Assessments
- **Method / Route:** `GET /api/v1/assessments`
- **Access:** Public / Authenticated
- **Query Parameters:** `status`, `page`, `page_size`.
- **Response (`200 OK`):** Paginated Assessment summary list.

#### 3. Get Assessment Details
- **Method / Route:** `GET /api/v1/assessments/{assessment_id}`
- **Access:** Authenticated
- **Response (`200 OK`):** Assessment metadata, schedule, and problem list.

#### 4. Assessment Plagiarism Report
- **Method / Route:** `GET /api/v1/assessments/{assessment_id}/plagiarism-report`
- **Access:** `ADMIN`, `RECRUITER`
- **Response (`200 OK`):**
```json
{
  "assessment_id": 1,
  "total_comparisons": 15,
  "high_risk_matches": [
    {
      "problem_id": 1,
      "candidate_a_id": 3,
      "candidate_a_name": "Alice Candidate",
      "submission_a_id": 101,
      "candidate_b_id": 4,
      "candidate_b_name": "Bob Candidate",
      "submission_b_id": 104,
      "similarity_percentage": 94.5,
      "flagged": true
    }
  ]
}
```

---

### Code Execution & Submissions (`/api/v1/submissions`)

#### 1. Dry Run Code Against Sample Test
- **Method / Route:** `POST /api/v1/submissions/run-sample`
- **Access:** Authenticated
- **Request Body:**
```json
{
  "problem_id": 1,
  "language": "PYTHON",
  "code": "import sys\nline = sys.stdin.read().strip()\nprint(line[::-1])",
  "custom_input": "hello world"
}
```
- **Response (`200 OK`):**
```json
{
  "status": "ACCEPTED",
  "stdout": "dlrow olleh\n",
  "stderr": "",
  "execution_time_ms": 42.1,
  "memory_used_mb": 14.2
}
```

#### 2. Submit Code for Formal Evaluation
- **Method / Route:** `POST /api/v1/submissions`
- **Access:** Authenticated (`CANDIDATE`, `RECRUITER`, `ADMIN`)
- **Request Body:**
```json
{
  "problem_id": 1,
  "assessment_id": 1,
  "language": "PYTHON",
  "code": "import sys\nnums = sys.stdin.read().split()\nprint(sum(map(int, nums)))"
}
```
- **Response (`201 Created`):**
```json
{
  "id": 105,
  "problem_id": 1,
  "assessment_id": 1,
  "candidate_id": 3,
  "language": "PYTHON",
  "status": "ACCEPTED",
  "score": 100.0,
  "max_score": 100.0,
  "execution_time_ms": 48.6,
  "memory_used_mb": 16.0,
  "test_case_results": [
    {
      "test_case_id": 1,
      "is_hidden": false,
      "status": "ACCEPTED",
      "execution_time_ms": 24.1,
      "stdout": "15\n",
      "expected_output": "15",
      "score_earned": 50.0,
      "max_score": 50.0
    },
    {
      "test_case_id": 2,
      "is_hidden": true,
      "status": "ACCEPTED",
      "execution_time_ms": 24.5,
      "stdout": null,
      "expected_output": null,
      "score_earned": 50.0,
      "max_score": 50.0
    }
  ],
  "created_at": "2026-09-19T10:15:00Z"
}
```

---

### Real-Time Leaderboards (`/api/v1/leaderboard`)

#### 1. Get Assessment Leaderboard
- **Method / Route:** `GET /api/v1/leaderboard/assessments/{assessment_id}`
- **Access:** Public / Authenticated
- **Ranking Rules:**
  1. Descending Total Score (`total_score DESC`).
  2. Ascending Total Execution Penalty / Submission Time (`submission_time ASC`).
- **Response (`200 OK`):**
```json
{
  "assessment_id": 1,
  "rankings": [
    {
      "rank": 1,
      "candidate_id": 3,
      "candidate_name": "Alice Candidate",
      "total_score": 100.0,
      "problems_solved": 2,
      "last_submission_time": "2026-09-19T10:30:00Z"
    },
    {
      "rank": 2,
      "candidate_id": 4,
      "candidate_name": "Bob Candidate",
      "total_score": 50.0,
      "problems_solved": 1,
      "last_submission_time": "2026-09-19T10:45:00Z"
    }
  ]
}
```

---

## 8. Cross-Platform Client Integration Guide

### Token Refresh State Machine (Web / Mobile / Desktop)

All clients should implement an HTTP interceptor that intercepts `401 Unauthorized` responses and refreshes the token without dropping active requests.

```mermaid
sequenceDiagram
    autonumber
    actor User as User Action
    participant Client as Frontend / Mobile App
    participant API as FastAPI Backend
    
    User->>Client: Execute Protected Action
    Client->>API: GET /api/v1/assessments/1 (Header: Bearer Token Expired)
    API-->>Client: HTTP 401 Unauthorized (AUTHENTICATION_ERROR)
    Note over Client: Interceptor halts queued requests
    Client->>API: POST /api/v1/auth/refresh-token (Body: refresh_token)
    alt Refresh Token Valid
        API-->>Client: HTTP 200 OK (New access_token + refresh_token)
        Note over Client: Update secure storage (Keychain / EncryptedSharedPreferences / LocalStorage)
        Client->>API: Re-send GET /api/v1/assessments/1 (New access_token)
        API-->>Client: HTTP 200 OK (Assessment Data)
        Client-->>User: Render Assessment View
    else Refresh Token Expired or Invalid
        API-->>Client: HTTP 401 Unauthorized
        Note over Client: Clear stored credentials
        Client-->>User: Redirect to Login Screen
    end
```

---

## 9. DevOps, Infrastructure & Production Deployment

### Docker Deployment

The application is containerized using a multi-runtime Linux image supporting both Python 3 and Node.js execution.

#### Single-Command Deployment
```bash
docker compose up -d --build
```

#### Production Environment Variables Configuration (`.env`)
```ini
PROJECT_NAME="Developer Assessment Platform API"
ENVIRONMENT="production"
DEBUG=false

DATABASE_URL="postgresql+asyncpg://postgres_user:secure_db_pass@postgres:5432/assessment_db"

JWT_SECRET_KEY="generate-a-cryptographically-random-64-char-string"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

CORS_ORIGINS=["https://assessment.yourdomain.com", "https://app.yourdomain.com"]

SANDBOX_TIMEOUT_SECONDS=5
SANDBOX_MAX_MEMORY_MB=128
SANDBOX_MAX_OUTPUT_BYTES=65536
```

### Production Nginx Reverse Proxy Configuration
```nginx
upstream fastapi_cluster {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name api.assessment.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.assessment.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.assessment.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.assessment.yourdomain.com/privkey.pem;

    client_max_body_size 10M;

    location / {
        proxy_pass http://fastapi_cluster;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }
}
```

---

## 10. Edge Cases and Resilience Engineering

1. **Infinite Loops and Fork Bombs:**
   - Mitigated via asynchronous subprocess timeouts (`asyncio.wait_for`) and OS process termination.
2. **Standard Output Buffer Exhaustion:**
   - Streams are read with hard truncation at 64 KB, preventing memory starvation on the host machine.
3. **Database Concurrency and Race Conditions:**
   - Submission scoring and assessment result updates use atomic database transactions.
4. **Timezone Discrepancies:**
   - All datetime values in requests and responses are strictly formatted in ISO 8601 UTC (`Z`).
5. **Score Tie-Breaking:**
   - In competitive assessment leaderboards, candidate rankings with identical total scores are ordered deterministically by the earliest timestamp of their last accepted submission.
