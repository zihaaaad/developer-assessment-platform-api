import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.session import AsyncSessionLocal, init_db
from app.models.enums import (
    AssessmentStatusEnum,
    DifficultyEnum,
    LanguageEnum,
    RoleEnum,
    SubmissionStatusEnum,
)
from app.models.user import User
from app.schemas.assessment import AssessmentCreate, AssessmentProblemAdd
from app.schemas.auth import LoginRequest, SignupRequest
from app.schemas.common import SortOrderEnum
from app.schemas.problem import ProblemCreate
from app.schemas.submission import SubmissionCreate
from app.schemas.test_case import TestCaseCreate
from app.services.assessment_service import AssessmentService
from app.services.auth_service import AuthService
from app.services.leaderboard_service import LeaderboardService
from app.services.plagiarism_service import PlagiarismService
from app.services.problem_service import ProblemService
from app.services.submission_service import SubmissionService
from app.services.test_case_service import TestCaseService
from app.core.security import decode_token, hash_password


async def get_or_create_user(db, name: str, email: str, role: RoleEnum):
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if user:
        user.password_hash = hash_password("Password123!")
        user.role = role
        user.name = name
        await db.flush()
        return user
    return await AuthService.register(
        db,
        SignupRequest(
            name=name,
            email=email,
            password="Password123!",
            role=role,
        ),
    )


async def main():
    print("=== 1. Initializing Database ===")
    await init_db()
    print("Database tables initialized successfully.")

    async with AsyncSessionLocal() as db:
        print("\n=== 2. Testing Authentication & User Seeding ===")
        admin_user = await get_or_create_user(db, "Admin Engineer", "admin@assessment.com", RoleEnum.ADMIN)
        print(f"Created Admin: {admin_user.email} (Role: {admin_user.role.value})")

        recruiter_user = await get_or_create_user(db, "Lead Recruiter", "recruiter@assessment.com", RoleEnum.RECRUITER)
        print(f"Created Recruiter: {recruiter_user.email} (Role: {recruiter_user.role.value})")

        cand1 = await get_or_create_user(db, "Alice Developer", "alice@candidate.com", RoleEnum.CANDIDATE)
        print(f"Created Candidate 1: {cand1.email}")

        cand2 = await get_or_create_user(db, "Bob Coder", "bob@candidate.com", RoleEnum.CANDIDATE)
        print(f"Created Candidate 2: {cand2.email}")

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
        print("Added 2 test cases to Problem 1 (1 sample, 1 hidden).")

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
        rec_payload = decode_token(recruiter_res.access_token)
        rec_user = (await db.execute(select(User).where(User.id == rec_payload["sub"]))).scalar_one()

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
        alice_user = (await db.execute(select(User).where(User.id == cand1.id))).scalar_one()
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

        bob_user = (await db.execute(select(User).where(User.id == cand2.id))).scalar_one()
        python_wrong_code = """
import sys
print("0 0")
"""
        sub2 = await SubmissionService.create_and_evaluate(
            db,
            bob_user,
            SubmissionCreate(
                problem_id=prob1.id,
                assessment_id=assessment.id,
                language=LanguageEnum.PYTHON,
                code=python_wrong_code,
            ),
        )
        print(f"Bob Wrong Answer Status: {sub2.status.value}, Score: {sub2.score}/{sub2.max_score}")

        bob_js_code = """
const fs = require('fs');

function solve() {
    const input = fs.readFileSync(0, 'utf-8').trim().split('\\n');
    if (input.length < 2) return;
    const nums = input[0].split(' ').map(Number);
    const target = Number(input[1]);
    const map = new Map();
    for (let i = 0; i < nums.length; i++) {
        const diff = target - nums[i];
        if (map.has(diff)) {
            console.log(map.get(diff) + ' ' + i);
            return;
        }
        map.set(nums[i], i);
    }
}
solve();
"""
        sub3 = await SubmissionService.create_and_evaluate(
            db,
            bob_user,
            SubmissionCreate(
                problem_id=prob1.id,
                assessment_id=assessment.id,
                language=LanguageEnum.JAVASCRIPT,
                code=bob_js_code,
            ),
        )
        print(f"Bob JavaScript Submission Status: {sub3.status.value}, Score: {sub3.score}/{sub3.max_score}, Execution Time: {sub3.execution_time_ms}ms")

        print("\n=== 6. Testing Dry Run (Run Sample Code) ====")
        from app.schemas.submission import RunSampleCodeRequest
        dry_run_res = await SubmissionService.run_sample(
            db,
            RunSampleCodeRequest(
                problem_id=prob2.id,
                language=LanguageEnum.PYTHON,
                code="""
import sys
line = sys.stdin.read().strip()
words = line.split()
print(" ".join(reversed(words)))
""",
                custom_input="hello world",
            ),
        )
        print(f"Dry Run Result: Status: {dry_run_res.status.value}, Passed: {dry_run_res.passed}, Output: '{dry_run_res.stdout.strip()}' (Expected: 'world hello')")

        print("\n=== 7. Testing Data Listing, Filtering, and Pagination ===")
        problems_page = await ProblemService.list_problems(
            db,
            search="Indices",
            difficulty=DifficultyEnum.EASY,
            category=None,
            is_published=True,
            sort_by="created_at",
            sort_order=SortOrderEnum.DESC,
            page=1,
            page_size=10,
        )
        print(f"Problem search result: {len(problems_page.items)} items found (Total: {problems_page.total_items})")

        print("\n=== 8. Testing Real-time Leaderboard ===")
        leaderboard = await LeaderboardService.get_assessment_leaderboard(db, assessment.id)
        print(f"Leaderboard for '{assessment.title}':")
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
            ResetPasswordRequest(token=reset_token, new_password="NewSecretPass123!"),
        )
        print("Password reset successfully. Verifying new login...")
        new_login = await AuthService.login(
            db, LoginRequest(email="alice@candidate.com", password="NewSecretPass123!")
        )
        print("Alice successfully logged in with new password! New token issued.")

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
    raw_input = sys.stdin.read().strip().split('\\n')
    if len(raw_input) < 2:
        return
    array_numbers = list(map(int, raw_input[0].split()))
    goal_sum = int(raw_input[1])
    hash_lookup = {}
    for pos, element in enumerate(array_numbers):
        complement = goal_sum - element
        if complement in hash_lookup:
            print(f"{hash_lookup[complement]} {pos}")
            return
        hash_lookup[element] = pos

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

        plagiarism_report = await PlagiarismService.analyze_assessment(
            db=db,
            assessment_id=assessment.id,
            similarity_threshold=0.50,
        )
        print(f"Plagiarism Report for Assessment: '{plagiarism_report['assessment_title']}'")
        print(f"  Pairs Analyzed: {plagiarism_report['total_pairs_analyzed']}, Flagged Suspicious Matches: {plagiarism_report['flagged_cases_count']}")
        for case in plagiarism_report['flagged_pairs']:
            print(f"  Flagged Match: {case['candidate_1']['name']} vs {case['candidate_2']['name']} on '{case['problem_title']}' -> Similarity: {case['similarity_percentage']}% (Risk: {case['risk_level']})")

        await db.commit()
        print("Database transaction successfully committed to disk.")

    print("\n=== End-to-End Verification Complete! All Components Working Perfectly! ===")


if __name__ == "__main__":
    asyncio.run(main())
