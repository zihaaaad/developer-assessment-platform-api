import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.session import AsyncSessionLocal, init_db
from app.models.enums import AssessmentStatusEnum, DifficultyEnum, RoleEnum
from app.schemas.assessment import AssessmentCreate, AssessmentProblemAdd
from app.schemas.problem import ProblemCreate
from app.schemas.test_case import TestCaseCreate
from app.services.assessment_service import AssessmentService
from app.services.problem_service import ProblemService
from app.services.test_case_service import TestCaseService
from app.core.security import hash_password
from app.models.user import User

async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        users = [
            ("Admin User", "admin@assessment.com", RoleEnum.ADMIN),
            ("Senior Recruiter", "recruiter@assessment.com", RoleEnum.RECRUITER),
            ("Alice Developer", "alice@candidate.com", RoleEnum.CANDIDATE),
            ("Bob Coder", "bob@candidate.com", RoleEnum.CANDIDATE),
        ]
        
        for name, email, role in users:
            stmt = select(User).where(User.email == email)
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                existing.password_hash = hash_password("Password123!")
                existing.role = role
                existing.name = name
            else:
                new_user = User(
                    email=email,
                    password_hash=hash_password("Password123!"),
                    name=name,
                    role=role,
                )
                db.add(new_user)
        await db.flush()

        additional_problems = [
            {
                "title": "Valid Parentheses Checker",
                "description": "Given a string `s` containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.\n\nAn input string is valid if:\n1. Open brackets must be closed by the same type of brackets.\n2. Open brackets must be closed in the correct order.\n3. Every close bracket has a corresponding open bracket of the same type.\n\nInput format: A single line with string `s`.\nOutput format: Print `true` if valid, otherwise `false`.",
                "difficulty": DifficultyEnum.EASY,
                "category": "Stack & Queue",
                "sample_input": "()[]{}",
                "sample_output": "true",
                "boilerplate_code": {
                    "python": "import sys\n\ndef isValid(s: str) -> bool:\n    stack = []\n    mapping = {')': '(', '}': '{', ']': '['}\n    for char in s:\n        if char in mapping:\n            top = stack.pop() if stack else '#'\n            if mapping[char] != top:\n                return False\n        else:\n            stack.append(char)\n    return not stack\n\nif __name__ == '__main__':\n    s = sys.stdin.read().strip()\n    print('true' if isValid(s) else 'false')",
                    "javascript": "const fs = require('fs');\nconst s = fs.readFileSync(0, 'utf-8').trim();\n\nfunction isValid(s) {\n    const stack = [];\n    const map = { ')': '(', '}': '{', ']': '[' };\n    for (let char of s) {\n        if (char in map) {\n            const top = stack.pop() || '#';\n            if (map[char] !== top) return false;\n        } else {\n            stack.push(char);\n        }\n    }\n    return stack.length === 0;\n}\n\nconsole.log(isValid(s) ? 'true' : 'false');"
                },
                "test_cases": [
                    {"input": "()", "output": "true", "hidden": False, "score": 30},
                    {"input": "()[]{}", "output": "true", "hidden": False, "score": 30},
                    {"input": "(]", "output": "false", "hidden": True, "score": 20},
                    {"input": "([)]", "output": "false", "hidden": True, "score": 20},
                ]
            },
            {
                "title": "Merge Intervals",
                "description": "Given an array of `intervals` where `intervals[i] = [start_i, end_i]`, merge all overlapping intervals, and return an array of the non-overlapping intervals that cover all the intervals in the input.\n\nInput format:\nLine 1: N (number of intervals)\nNext N lines: start and end separated by space.\n\nOutput format:\nMerged intervals one per line.",
                "difficulty": DifficultyEnum.MEDIUM,
                "category": "Arrays",
                "sample_input": "4\n1 3\n2 6\n8 10\n15 18",
                "sample_output": "1 6\n8 10\n15 18",
                "boilerplate_code": {
                    "python": "import sys\n\ndef solve():\n    lines = sys.stdin.read().strip().split('\\n')\n    if not lines or not lines[0]: return\n    n = int(lines[0])\n    intervals = []\n    for i in range(1, n + 1):\n        if i < len(lines):\n            parts = list(map(int, lines[i].split()))\n            if len(parts) == 2: intervals.append(parts)\n    \n    intervals.sort(key=lambda x: x[0])\n    merged = []\n    for interval in intervals:\n        if not merged or merged[-1][1] < interval[0]:\n            merged.append(interval)\n        else:\n            merged[-1][1] = max(merged[-1][1], interval[1])\n            \n    for m in merged:\n        print(f\"{m[0]} {m[1]}\")\n\nif __name__ == '__main__':\n    solve()",
                    "javascript": "const fs = require('fs');\nconst input = fs.readFileSync(0, 'utf-8').trim().split('\\n');\nfunction solve() {\n    if (!input || !input[0]) return;\n    const n = parseInt(input[0]);\n    const intervals = [];\n    for (let i = 1; i <= n && i < input.length; i++) {\n        const parts = input[i].trim().split(/\\s+/).map(Number);\n        if (parts.length === 2) intervals.push(parts);\n    }\n    intervals.sort((a, b) => a[0] - b[0]);\n    const merged = [];\n    for (const cur of intervals) {\n        if (merged.length === 0 || merged[merged.length - 1][1] < cur[0]) {\n            merged.push(cur);\n        } else {\n            merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], cur[1]);\n        }\n    }\n    for (const m of merged) {\n        console.log(`${m[0]} ${m[1]}`);\n    }\n}\nsolve();"
                },
                "test_cases": [
                    {"input": "4\n1 3\n2 6\n8 10\n15 18", "output": "1 6\n8 10\n15 18", "hidden": False, "score": 50},
                    {"input": "2\n1 4\n4 5", "output": "1 5", "hidden": True, "score": 50},
                ]
            },
            {
                "title": "Coin Change Minimum",
                "description": "You are given an integer array `coins` representing coins of different denominations and an integer `amount` representing a total amount of money.\n\nReturn the fewest number of coins that you need to make up that amount. If that amount of money cannot be made up by any combination of the coins, return `-1`.\n\nInput format:\nLine 1: space-separated coins\nLine 2: amount\n\nOutput format: Integer representing min coins or -1.",
                "difficulty": DifficultyEnum.MEDIUM,
                "category": "Dynamic Programming",
                "sample_input": "1 2 5\n11",
                "sample_output": "3",
                "boilerplate_code": {
                    "python": "import sys\n\ndef coinChange():\n    lines = sys.stdin.read().strip().split('\\n')\n    coins = list(map(int, lines[0].split()))\n    amount = int(lines[1])\n    dp = [float('inf')] * (amount + 1)\n    dp[0] = 0\n    for coin in coins:\n        for x in range(coin, amount + 1):\n            dp[x] = min(dp[x], dp[x - coin] + 1)\n    print(dp[amount] if dp[amount] != float('inf') else -1)\n\nif __name__ == '__main__':\n    coinChange()",
                    "javascript": "const fs = require('fs');\nconst lines = fs.readFileSync(0, 'utf-8').trim().split('\\n');\nfunction coinChange() {\n    if (lines.length < 2) return;\n    const coins = lines[0].trim().split(/\\s+/).map(Number);\n    const amount = parseInt(lines[1]);\n    const dp = new Array(amount + 1).fill(Infinity);\n    dp[0] = 0;\n    for (const coin of coins) {\n        for (let x = coin; x <= amount; x++) {\n            dp[x] = Math.min(dp[x], dp[x - coin] + 1);\n        }\n    }\n    console.log(dp[amount] !== Infinity ? dp[amount] : -1);\n}\ncoinChange();"
                },
                "test_cases": [
                    {"input": "1 2 5\n11", "output": "3", "hidden": False, "score": 50},
                    {"input": "2\n3", "output": "-1", "hidden": True, "score": 50},
                ]
            }
        ]

        created_prob_ids = []
        for p_data in additional_problems:
            try:
                prob = await ProblemService.create_problem(
                    db,
                    ProblemCreate(
                        title=p_data["title"],
                        description=p_data["description"],
                        difficulty=p_data["difficulty"],
                        category=p_data["category"],
                        time_limit_ms=2000,
                        memory_limit_mb=128,
                        sample_input=p_data["sample_input"],
                        sample_output=p_data["sample_output"],
                        boilerplate_code=p_data["boilerplate_code"],
                        is_published=True,
                    )
                )
                created_prob_ids.append(prob.id)
                for tc in p_data["test_cases"]:
                    await TestCaseService.create_test_case(
                        db,
                        prob.id,
                        TestCaseCreate(
                            input_data=tc["input"],
                            expected_output=tc["output"],
                            is_hidden=tc["hidden"],
                            score_weight=tc["score"]
                        )
                    )
                print(f"Created problem: {p_data['title']}")
            except Exception as e:
                print(f"Skipping existing problem {p_data['title']}: {e}")

        stmt = select(User).where(User.email == "recruiter@assessment.com")
        res = await db.execute(stmt)
        recruiter = res.scalar_one_or_none()
        
        now = datetime.now(timezone.utc)
        if recruiter:
            try:
                assess = await AssessmentService.create_assessment(
                    db,
                    recruiter,
                    AssessmentCreate(
                        title="Core Algorithms & Data Structures Assessment",
                        description="Timed technical screening assessing problem-solving in Arrays, Stacks, and Dynamic Programming.",
                        start_time=now - timedelta(hours=1),
                        end_time=now + timedelta(days=5),
                        duration_minutes=90,
                        passing_score=100,
                        status=AssessmentStatusEnum.PUBLISHED,
                    )
                )
                if created_prob_ids:
                    for idx, pid in enumerate(created_prob_ids):
                        await AssessmentService.add_problem(
                            db,
                            assess.id,
                            AssessmentProblemAdd(problem_id=pid, order_index=idx+1, points=100),
                            recruiter
                        )
                print(f"Created Assessment: {assess.title}")
            except Exception as e:
                print(f"Assessment note: {e}")

        await db.commit()
        print("Rich data seeded and committed successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
