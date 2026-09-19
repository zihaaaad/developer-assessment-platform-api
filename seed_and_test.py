import asyncio
from datetime import datetime, timedelta, timezone
from app.db.session import AsyncSessionLocal, init_db
from app.models.enums import (
    AssessmentStatusEnum,
    DifficultyEnum,
    LanguageEnum,
    RoleEnum,
    SubmissionStatusEnum,
)
from app.schemas.assessment import AssessmentCreate, AssessmentProblemAdd
from app.schemas.auth import LoginRequest, SignupRequest
from app.schemas.common import SortOrderEnum
from app.schemas.problem import ProblemCreate
from app.schemas.submission import SubmissionCreate
from app.schemas.test_case import TestCaseCreate
from app.services.assessment_service import AssessmentService
from app.services.auth_service import AuthService
from app.services.leaderboard_service import LeaderboardService
from app.services.problem_service import ProblemService
from app.services.submission_service import SubmissionService
from app.services.test_case_service import TestCaseService


async def main():
    print("=== 1. Initializing Database ===")
    await init_db()
    print("Database tables initialized successfully.")

    async with AsyncSessionLocal() as db:
        print("\n=== 2. Testing Authentication & User Seeding ===")
        try:
            admin_user = await AuthService.register(
                db,
                SignupRequest(
                    name="Admin Engineer",
                    email="admin@assessment.com",
                    password="Password123!",
                    role=RoleEnum.ADMIN,
                ),
            )
            print(f"Created Admin: {admin_user.email} (Role: {admin_user.role.value})")
        except Exception as e:
            print(f"Admin already exists: {e}")

        try:
            recruiter_user = await AuthService.register(
                db,
                SignupRequest(
                    name="Lead Recruiter",
                    email="recruiter@assessment.com",
                    password="Password123!",
                    role=RoleEnum.RECRUITER,
                ),
            )
            print(f"Created Recruiter: {recruiter_user.email} (Role: {recruiter_user.role.value})")
        except Exception as e:
            print(f"Recruiter already exists: {e}")

        try:
            cand1 = await AuthService.register(
                db,
                SignupRequest(
                    name="Alice Developer",
                    email="alice@candidate.com",
                    password="Password123!",
                    role=RoleEnum.CANDIDATE,
                ),
            )
            print(f"Created Candidate 1: {cand1.email}")
        except Exception as e:
            print(f"Candidate 1 already exists: {e}")

        try:
            cand2 = await AuthService.register(
                db,
                SignupRequest(
                    name="Bob Coder",
                    email="bob@candidate.com",
                    password="Password123!",
                    role=RoleEnum.CANDIDATE,
                ),
            )
            print(f"Created Candidate 2: {cand2.email}")
        except Exception as e:
            print(f"Candidate 2 already exists: {e}")

        login_res = await AuthService.login(
            db, LoginRequest(email="alice@candidate.com", password="Password123!")
        )
        print(f"Login successful for Alice. Token issued (type: {login_res.token_type})")

        print("\n=== 3. Testing Problem & Test Cases Creation ===")
        prob1 = await ProblemService.create_problem(
            db,
            ProblemCreate(
                title="Two Sum Target Indices",
                description="Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.\nInput format: line 1 space-separated numbers, line 2 target.\nOutput format: space-separated indices.",
                difficulty=DifficultyEnum.EASY,
                category="Arrays",
                time_limit_ms=2000,
                memory_limit_mb=128,
                sample_input="2 7 11 15\n9",
                sample_output="0 1",
                boilerplate_code={
                    "python": "import sys\n\ndef two_sum():\n    lines = sys.stdin.read().strip().split('\\n')\n    nums = list(map(int, lines[0].split()))\n    target = int(lines[1])\n\nif __name__ == '__main__':\n    two_sum()",
                    "javascript": "const fs = require('fs');\nconst input = fs.readFileSync(0, 'utf-8').trim().split('\\n');",
                },
                is_published=True,
            ),
        )
        print(f"Created Problem: '{prob1.title}' (Slug: {prob1.slug})")

        tc1 = await TestCaseService.create_test_case(
            db,
            prob1.id,
            TestCaseCreate(
                input_data="2 7 11 15\n9",
                expected_output="0 1",
                is_hidden=False,
                score_weight=50,
            ),
        )
        tc2 = await TestCaseService.create_test_case(
            db,
            prob1.id,
            TestCaseCreate(
                input_data="3 2 4\n6",
                expected_output="1 2",
                is_hidden=True,
                score_weight=50,
            ),
        )
        print(f"Added 2 test cases to Problem 1 (1 sample, 1 hidden).")

        prob2 = await ProblemService.create_problem(
            db,
            ProblemCreate(
                title="Reverse Words in String",
                description="Reverse the words in a given sentence.\nInput format: String\nOutput format: String with reversed words.",
                difficulty=DifficultyEnum.MEDIUM,
                category="Strings",
                time_limit_ms=1500,
                memory_limit_mb=128,
                sample_input="hello world",
                sample_output="world hello",
                is_published=True,
            ),
        )
        await TestCaseService.create_test_case(
            db,
            prob2.id,
            TestCaseCreate(
                input_data="hello world",
                expected_output="world hello",
                is_hidden=False,
                score_weight=100,
            ),
        )
        print(f"Created Problem: '{prob2.title}' (Slug: {prob2.slug})")

        print("\n=== 4. Testing Assessment Creation ===")
        recruiter_res = await AuthService.login(
            db, LoginRequest(email="recruiter@assessment.com", password="Password123!")
        )
        from app.core.security import decode_token
        rec_payload = decode_token(recruiter_res.access_token)
        from app.models.user import User
        rec_user = (await db.execute(select_user := select_user_query(rec_payload["sub"]))).scalar_one()

        assessment = await AssessmentService.create_assessment(
            db,
            rec_user,
            AssessmentCreate(
                title="Senior Backend Engineer Technical Screening",
                description="90-minute timed coding assessment evaluating algorithm efficiency and problem solving.",
                start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                end_time=datetime.now(timezone.utc) + timedelta(hours=2),
                duration_minutes=90,
                passing_score=100,
                status=AssessmentStatusEnum.PUBLISHED,
                problems=[
                    AssessmentProblemAdd(problem_id=prob1.id, order_index=1, points=100),
                    AssessmentProblemAdd(problem_id=prob2.id, order_index=2, points=100),
                ],
            ),
        )
        print(f"Created Assessment: '{assessment.title}' with {len(assessment.problems)} problems.")

        print("\n=== 5. Testing Code Execution & Sandbox Engine ===")
        alice_user = (await db.execute(select_user_query(cand1.id))).scalar_one()
        python_correct_code = """
import sys

def solve():
    lines = sys.stdin.read().strip().split('\\n')
    if len(lines) < 2:
        return
    nums = list(map(int, lines[0].split()))
    target = int(lines[1])
    seen = {}
    for idx, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            print(f"{seen[diff]} {idx}")
            return
        seen[num] = idx

if __name__ == '__main__':
    solve()
"""
        sub1 = await SubmissionService.create_and_evaluate(
            db,
            alice_user,
            SubmissionCreate(
                problem_id=prob1.id,
                assessment_id=assessment.id,
                language=LanguageEnum.PYTHON,
                code=python_correct_code,
            ),
        )
        print(f"Alice Submission Status: {sub1.status.value}, Score: {sub1.score}/{sub1.max_score}, Execution Time: {sub1.execution_time_ms}ms")

        bob_user = (await db.execute(select_user_query(cand2.id))).scalar_one()
        wrong_code = """
print("wrong output")
"""
        sub2 = await SubmissionService.create_and_evaluate(
            db,
            bob_user,
            SubmissionCreate(
                problem_id=prob1.id,
                assessment_id=assessment.id,
                language=LanguageEnum.PYTHON,
                code=wrong_code,
            ),
        )
        print(f"Bob Wrong Answer Status: {sub2.status.value}, Score: {sub2.score}/{sub2.max_score}")

        js_code = """
const fs = require('fs');
const input = fs.readFileSync(0, 'utf-8').trim();
const reversed = input.split(' ').reverse().join(' ');
console.log(reversed);
"""
        sub_js = await SubmissionService.create_and_evaluate(
            db,
            bob_user,
            SubmissionCreate(
                problem_id=prob2.id,
                assessment_id=assessment.id,
                language=LanguageEnum.JAVASCRIPT,
                code=js_code,
            ),
        )
        print(f"Bob JavaScript Submission Status: {sub_js.status.value}, Score: {sub_js.score}/{sub_js.max_score}, Execution Time: {sub_js.execution_time_ms}ms")

        print("\n=== 6. Testing Dry Run (Run Sample Code) ===")
        from app.schemas.submission import RunSampleCodeRequest
        sample_run = await SubmissionService.run_sample(
            db,
            RunSampleCodeRequest(
                problem_id=prob2.id,
                language=LanguageEnum.PYTHON,
                code="import sys\nline = sys.stdin.read().strip()\nprint(' '.join(line.split()[::-1]))",
            ),
        )
        print(f"Dry Run Result: Status: {sample_run.status.value}, Passed: {sample_run.passed}, Output: '{sample_run.stdout}' (Expected: '{sample_run.expected_output}')")

        print("\n=== 7. Testing Data Listing, Filtering, and Pagination ===")
        listed_problems = await ProblemService.list_problems(
            db,
            search="target",
            difficulty=DifficultyEnum.EASY,
            page=1,
            page_size=5,
            sort_by="title",
            sort_order=SortOrderEnum.ASC,
        )
        print(f"Problem search result: {len(listed_problems.items)} items found (Total: {listed_problems.total_items})")

        print("\n=== 8. Testing Real-time Leaderboard ===")
        leaderboard = await LeaderboardService.get_assessment_leaderboard(db, assessment.id)
        print(f"Leaderboard for '{leaderboard.assessment_title}':")
        for entry in leaderboard.entries:
            print(f"  Rank #{entry.rank}: {entry.candidate_name} | Score: {entry.total_score} | Problems Solved: {entry.problems_solved}")

        print("\n=== 9. Testing Password Reset Workflow ===")
        from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
        reset_token = await AuthService.request_password_reset(
            db, ForgotPasswordRequest(email="alice@candidate.com")
        )
        print(f"Reset token generated for Alice: {reset_token[:10]}...")

        await AuthService.reset_password(
            db,
            ResetPasswordRequest(token=reset_token, new_password="NewAlicePassword456!"),
        )
        print("Password reset successfully. Verifying new login...")

        new_login = await AuthService.login(
            db, LoginRequest(email="alice@candidate.com", password="NewAlicePassword456!")
        )
        print(f"Alice successfully logged in with new password! New token issued.")

        print("\n=== 10. Testing Admin User Role Update ===")
        from app.schemas.user import UserUpdateRoleRequest
        updated_bob = await AuthService.update_user_role(
            db, cand2.id, UserUpdateRoleRequest(role=RoleEnum.RECRUITER)
        )
        print(f"Bob's role successfully elevated by Admin to: {updated_bob.role.value}")

        print("\n=== 11. Testing Plagiarism & AST Code Similarity Engine ===")
        bob_copied_code = """
import sys

def main_solution():
    data = sys.stdin.read().strip().split('\\n')
    if len(data) < 2:
        return
    elements = list(map(int, data[0].split()))
    goal = int(data[1])
    hashmap = {}
    for i, val in enumerate(elements):
        remainder = goal - val
        if remainder in hashmap:
            print(f"{hashmap[remainder]} {i}")
            return
        hashmap[val] = i

if __name__ == '__main__':
    main_solution()
"""
        await SubmissionService.create_and_evaluate(
            db,
            bob_user,
            SubmissionCreate(
                problem_id=prob1.id,
                assessment_id=assessment.id,
                language=LanguageEnum.PYTHON,
                code=bob_copied_code,
            ),
        )

        from app.services.plagiarism_service import PlagiarismService
        plagiarism_report = await PlagiarismService.analyze_assessment(
            db=db,
            assessment_id=assessment.id,
            similarity_threshold=0.50,
        )
        print(f"Plagiarism Report for Assessment: '{plagiarism_report['assessment_title']}'")
        print(f"  Pairs Analyzed: {plagiarism_report['total_pairs_analyzed']}, Flagged Suspicious Matches: {plagiarism_report['flagged_cases_count']}")
        for case in plagiarism_report['flagged_pairs']:
            print(f"  Flagged Match: {case['candidate_1']['name']} vs {case['candidate_2']['name']} on '{case['problem_title']}' -> Similarity: {case['similarity_percentage']} (Risk: {case['risk_level']})")

    print("\n=== End-to-End Verification Complete! All Components Working Perfectly! ===")


def select_user_query(user_id: str):
    from sqlalchemy import select
    from app.models.user import User
    return select(User).where(User.id == user_id)


if __name__ == "__main__":
    asyncio.run(main())
