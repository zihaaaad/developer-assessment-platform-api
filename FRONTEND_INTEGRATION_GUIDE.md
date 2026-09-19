# Frontend Developer Integration Guide
### Developer Assessment & Coding Platform API

---

## 1. Quick Overview for Frontend Engineers

* **Base API URL:** `http://localhost:8000/api/v1`
* **Swagger Interactive Docs:** `http://localhost:8000/docs`
* **Authentication Scheme:** Standard HTTP Bearer Token (`Authorization: Bearer <access_token>`)
* **Supported Execution Languages:** `python`, `javascript`
* **Supported User Roles:** `CANDIDATE`, `RECRUITER`, `ADMIN`

---

## 2. Global Response Envelope Conventions

Every endpoint returns a consistent JSON envelope. Frontend API clients can rely on predictable schemas for state management.

### Standard Success Envelope
```json
{
  "success": true,
  "message": "Operation successful",
  "data": {}
}
```

### Paginated List Envelope
```json
{
  "success": true,
  "message": "Data retrieved successfully",
  "pagination": {
    "total_items": 45,
    "total_pages": 5,
    "current_page": 1,
    "page_size": 10,
    "has_next": true,
    "has_prev": false
  },
  "data": []
}
```

### Standard Error Envelope (HTTP 400, 401, 403, 404, 422)
```json
{
  "success": false,
  "message": "Input validation failed",
  "errors": [
    {
      "field": "body -> email",
      "message": "value is not a valid email address",
      "type": "value_error"
    }
  ]
}
```

---

## 3. User Roles and Core UI Flows

```text
+───────────────────────────────────────────────────────────────────────────+
│ CANDIDATE WORKFLOW                                                        │
│ 1. Signup / Login -> Store Access Token & Refresh Token                   │
│ 2. Browse Problem Catalog (Search, Difficulty Filter, Category Filter)    │
│ 3. Open Problem Workspace (View description, constraints, boilerplate)    │
│ 4. Click "Run Code" -> Instant feedback against visible sample inputs     │
│ 5. Click "Submit" -> Full evaluation against visible & hidden test cases  │
│ 6. Join Timed Assessment -> Live countdown timer -> View Leaderboard      │
+───────────────────────────────────────────────────────────────────────────+

+───────────────────────────────────────────────────────────────────────────+
│ RECRUITER WORKFLOW                                                        │
│ 1. Dashboard -> Create Coding Problem -> Add Visible & Hidden Test Cases  │
│ 2. Create Assessment -> Set Start/End Time, Duration, and Passing Score  │
│ 3. Assign Problems with Custom Point Weights                              │
│ 4. Monitor Live Candidate Leaderboard during test window                  │
│ 5. View Plagiarism Report (Automated AST similarity matching)             │
+───────────────────────────────────────────────────────────────────────────+

+───────────────────────────────────────────────────────────────────────────+
│ ADMIN WORKFLOW                                                            │
│ 1. User Management -> Search users by name/email, filter by role          │
│ 2. Promote or Demote Roles (CANDIDATE <-> RECRUITER <-> ADMIN)            │
│ 3. Delete / Terminate User Accounts                                      │
+───────────────────────────────────────────────────────────────────────────+
```

---

## 4. API Endpoints Reference

### Authentication & Profile (`/auth`)

#### 1. Signup (Register Account)
* **Method:** `POST`
* **URL:** `/api/v1/auth/signup`
* **Access:** Public
* **Request Body:**
```json
{
  "name": "Alice Developer",
  "email": "alice@example.com",
  "password": "Password123!",
  "role": "CANDIDATE"
}
```

#### 2. Login
* **Method:** `POST`
* **URL:** `/api/v1/auth/login`
* **Access:** Public
* **Request Body:**
```json
{
  "email": "alice@example.com",
  "password": "Password123!"
}
```
* **Response Body (`data`):**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

#### 3. Refresh Access Token
* **Method:** `POST`
* **URL:** `/api/v1/auth/refresh-token`
* **Request Body:**
```json
{
  "refresh_token": "eyJhbGciOi..."
}
```

#### 4. Forgot Password
* **Method:** `POST`
* **URL:** `/api/v1/auth/forgot-password`
* **Request Body:**
```json
{
  "email": "alice@example.com"
}
```

#### 5. Reset Password
* **Method:** `POST`
* **URL:** `/api/v1/auth/reset-password`
* **Request Body:**
```json
{
  "token": "o3nF3C9vHq...",
  "new_password": "NewSecretPassword123!"
}
```

#### 6. Get Current User Profile
* **Method:** `GET`
* **URL:** `/api/v1/auth/me`
* **Headers:** `Authorization: Bearer <access_token>`

#### 7. Update Profile / Change Password
* **Method:** `PUT`
* **URL:** `/api/v1/auth/me`
* **Headers:** `Authorization: Bearer <access_token>`
* **Request Body:**
```json
{
  "name": "Alice D. Updated",
  "current_password": "Password123!",
  "new_password": "BrandNewPassword123!"
}
```

---

### Coding Problems (`/problems`)

#### 1. List Problems (With Search, Filter, Sort, and Pagination)
* **Method:** `GET`
* **URL:** `/api/v1/problems`
* **Query Parameters:**
  * `search` (string, optional) - Search by title, slug, or category
  * `difficulty` (string, optional) - `EASY`, `MEDIUM`, or `HARD`
  * `category` (string, optional) - e.g. `Arrays`, `Strings`, `DP`
  * `sort_by` (string, optional) - `created_at`, `title`, `difficulty`, `category`, `time_limit_ms`
  * `sort_order` (string, optional) - `asc` or `desc` (default: `desc`)
  * `page` (integer, optional) - Page number (default: `1`)
  * `limit` (integer, optional) - Items per page (default: `10`, max: `100`)

#### 2. Get Problem Workspace Detail
* **Method:** `GET`
* **URL:** `/api/v1/problems/{id_or_slug}`
* **Response Body (`data`):**
```json
{
  "id": "b3e21a...",
  "title": "Two Sum Target Indices",
  "slug": "two-sum-target-indices",
  "description": "Given an array of integers nums and an integer target, return indices...",
  "difficulty": "EASY",
  "category": "Arrays",
  "time_limit_ms": 2000,
  "memory_limit_mb": 128,
  "sample_input": "2 7 11 15\n9",
  "sample_output": "0 1",
  "boilerplate_code": {
    "python": "import sys\n\ndef solve():\n    pass\n\nif __name__ == '__main__':\n    solve()",
    "javascript": "const fs = require('fs');\nconst input = fs.readFileSync(0, 'utf-8');\nconsole.log(input);"
  },
  "sample_test_cases": [
    {
      "id": "tc_1",
      "problem_id": "b3e21a...",
      "input_data": "2 7 11 15\n9",
      "expected_output": "0 1",
      "score_weight": 50
    }
  ]
}
```

#### 3. Create Problem *(Recruiter / Admin Only)*
* **Method:** `POST`
* **URL:** `/api/v1/problems`
* **Headers:** `Authorization: Bearer <recruiter_token>`
* **Request Body:**
```json
{
  "title": "Palindrome String Checker",
  "description": "Determine if a string is a palindrome ignoring cases.",
  "difficulty": "EASY",
  "category": "Strings",
  "time_limit_ms": 2000,
  "memory_limit_mb": 128,
  "sample_input": "racecar",
  "sample_output": "true",
  "boilerplate_code": {
    "python": "import sys\n# Code here",
    "javascript": "// Code here"
  },
  "is_published": true
}
```

---

### Test Cases (`/problems/{id}/test-cases` & `/test-cases/{id}`) *(Recruiter / Admin Only)*

#### 1. Add Test Case to Problem
* **Method:** `POST`
* **URL:** `/api/v1/problems/{problem_id}/test-cases`
* **Request Body:**
```json
{
  "input_data": "racecar",
  "expected_output": "true",
  "is_hidden": false,
  "score_weight": 50
}
```

#### 2. List All Test Cases for a Problem
* **Method:** `GET`
* **URL:** `/api/v1/problems/{problem_id}/test-cases`

#### 3. Update Test Case
* **Method:** `PUT`
* **URL:** `/api/v1/test-cases/{test_case_id}`

#### 4. Delete Test Case
* **Method:** `DELETE`
* **URL:** `/api/v1/test-cases/{test_case_id}`

---

### Code Execution & Submissions (`/submissions`)

#### 1. Dry Run / Run Sample Code (Instant Feedback)
* **Method:** `POST`
* **URL:** `/api/v1/submissions/run-sample`
* **Headers:** `Authorization: Bearer <candidate_token>`
* **Request Body:**
```json
{
  "problem_id": "b3e21a...",
  "language": "python",
  "code": "import sys\nlines = sys.stdin.read().split()\nprint('0 1')",
  "custom_input": null
}
```
* **Response (`data`):**
```json
{
  "status": "ACCEPTED",
  "stdout": "0 1",
  "stderr": "",
  "execution_time_ms": 42,
  "expected_output": "0 1",
  "passed": true,
  "error_message": null
}
```

#### 2. Submit Solution (Formal Evaluation & Scoring)
* **Method:** `POST`
* **URL:** `/api/v1/submissions`
* **Headers:** `Authorization: Bearer <candidate_token>`
* **Request Body:**
```json
{
  "problem_id": "b3e21a...",
  "assessment_id": "assess_456",
  "language": "python",
  "code": "import sys\ndef solve():\n    pass\nif __name__ == '__main__':\n    solve()"
}
```

#### 3. List Past Submissions
* **Method:** `GET`
* **URL:** `/api/v1/submissions?problem_id={id}&status={status}&page=1&limit=10`

---

### Assessments & Contests (`/assessments`)

#### 1. List Assessments
* **Method:** `GET`
* **URL:** `/api/v1/assessments?status=PUBLISHED&page=1&limit=10`

#### 2. Get Assessment Details & Assigned Problems
* **Method:** `GET`
* **URL:** `/api/v1/assessments/{assessment_id}`

#### 3. Create Assessment *(Recruiter / Admin)*
* **Method:** `POST`
* **URL:** `/api/v1/assessments`
* **Headers:** `Authorization: Bearer <recruiter_token>`
* **Request Body:**
```json
{
  "title": "Frontend Engineer Technical Screening",
  "description": "90-minute timed JavaScript and algorithms assessment.",
  "start_time": "2026-09-19T10:00:00Z",
  "end_time": "2026-09-19T14:00:00Z",
  "duration_minutes": 90,
  "passing_score": 100,
  "status": "PUBLISHED",
  "problems": [
    { "problem_id": "prob_1", "order_index": 1, "points": 100 },
    { "problem_id": "prob_2", "order_index": 2, "points": 100 }
  ]
}
```

#### 4. Get Plagiarism & Similarity Report *(Recruiter / Admin)*
* **Method:** `GET`
* **URL:** `/api/v1/assessments/{assessment_id}/plagiarism-report?threshold=0.70`
* **Headers:** `Authorization: Bearer <recruiter_token>`

---

### Real-Time Leaderboard (`/leaderboard`)

#### 1. Get Ranked Assessment Leaderboard
* **Method:** `GET`
* **URL:** `/api/v1/leaderboard/assessments/{assessment_id}`
* **Response (`data`):**
```json
{
  "assessment_id": "assess_456",
  "assessment_title": "Senior Technical Screening",
  "total_candidates": 2,
  "entries": [
    {
      "rank": 1,
      "candidate_id": "cand_1",
      "candidate_name": "Alice Developer",
      "total_score": 200,
      "problems_solved": 2,
      "total_time_seconds": 340
    },
    {
      "rank": 2,
      "candidate_id": "cand_2",
      "candidate_name": "Bob Coder",
      "total_score": 100,
      "problems_solved": 1,
      "total_time_seconds": 180
    }
  ]
}
```

---

## 5. Production-Ready Frontend Integration Snippet (Axios + TypeScript)

```typescript
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const res = await axios.post('http://localhost:8000/api/v1/auth/refresh-token', {
            refresh_token: refreshToken,
          });
          const newAccessToken = res.data.data.access_token;
          const newRefreshToken = res.data.data.refresh_token;

          localStorage.setItem('access_token', newAccessToken);
          localStorage.setItem('refresh_token', newRefreshToken);

          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          return apiClient(originalRequest);
        } catch (refreshErr) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);
```

---

## 6. Default Test Accounts

| Role | Email | Password |
| :--- | :--- | :--- |
| **Admin** | `admin@assessment.com` | `Password123!` |
| **Recruiter** | `recruiter@assessment.com` | `Password123!` |
| **Candidate 1** | `alice@candidate.com` | `Password123!` |
| **Candidate 2** | `bob@candidate.com` | `Password123!` |
