import ast
import re
from typing import Any, Dict, List, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.models.assessment import Assessment
from app.models.submission import Submission
from app.models.user import User


class PlagiarismService:
    @staticmethod
    def extract_ast_token_sequence(code: str) -> List[str]:
        try:
            tree = ast.parse(code)
            tokens: List[str] = []
            for node in ast.walk(tree):
                tokens.append(type(node).__name__)
            return tokens
        except SyntaxError:
            cleaned = re.sub(r"#.*", "", code)
            cleaned = re.sub(r'["\'].*?["\']', "STR", cleaned)
            cleaned = re.sub(r"\b\d+\b", "NUM", cleaned)
            words = re.findall(r"\b[a-zA-Z_]\w*\b|[^\w\s]", cleaned)
            return words

    @staticmethod
    def calculate_jaccard_similarity(tokens1: List[str], tokens2: List[str], n: int = 3) -> float:
        if not tokens1 or not tokens2:
            return 0.0

        def get_ngrams(tokens: List[str], n_size: int) -> Set[str]:
            if len(tokens) < n_size:
                return {"_".join(tokens)}
            return {"_".join(tokens[i : i + n_size]) for i in range(len(tokens) - n_size + 1)}

        ngrams1 = get_ngrams(tokens1, n)
        ngrams2 = get_ngrams(tokens2, n)

        intersection = ngrams1.intersection(ngrams2)
        union = ngrams1.union(ngrams2)

        if not union:
            return 0.0

        return round(len(intersection) / len(union), 4)

    @classmethod
    async def analyze_assessment(
        cls, db: AsyncSession, assessment_id: str, similarity_threshold: float = 0.70
    ) -> Dict[str, Any]:
        assess_res = await db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = assess_res.scalar_one_or_none()
        if not assessment:
            raise NotFoundException(message=f"Assessment '{assessment_id}' not found")

        query = (
            select(Submission)
            .where(
                Submission.assessment_id == assessment_id,
                Submission.score > 0,
            )
            .options(selectinload(Submission.candidate), selectinload(Submission.problem))
        )
        sub_res = await db.execute(query)
        submissions = sub_res.scalars().all()

        problems_map: Dict[str, Dict[str, Submission]] = {}
        for sub in submissions:
            p_id = sub.problem_id
            if p_id not in problems_map:
                problems_map[p_id] = {}

            c_id = sub.candidate_id
            if c_id not in problems_map[p_id] or sub.score > problems_map[p_id][c_id].score:
                problems_map[p_id][c_id] = sub

        flagged_pairs: List[Dict[str, Any]] = []

        for p_id, candidate_subs in problems_map.items():
            candidates = list(candidate_subs.keys())
            for i in range(len(candidates)):
                for j in range(i + 1, len(candidates)):
                    cand1_id = candidates[i]
                    cand2_id = candidates[j]

                    sub1 = candidate_subs[cand1_id]
                    sub2 = candidate_subs[cand2_id]

                    tokens1 = cls.extract_ast_token_sequence(sub1.code)
                    tokens2 = cls.extract_ast_token_sequence(sub2.code)

                    score = cls.calculate_jaccard_similarity(tokens1, tokens2)

                    if score >= similarity_threshold:
                        flagged_pairs.append(
                            {
                                "problem_id": p_id,
                                "problem_title": sub1.problem.title,
                                "similarity_score": score,
                                "similarity_percentage": f"{score * 100:.1f}%",
                                "candidate_1": {
                                    "id": sub1.candidate.id,
                                    "name": sub1.candidate.name,
                                    "email": sub1.candidate.email,
                                    "submission_id": sub1.id,
                                },
                                "candidate_2": {
                                    "id": sub2.candidate.id,
                                    "name": sub2.candidate.name,
                                    "email": sub2.candidate.email,
                                    "submission_id": sub2.id,
                                },
                                "risk_level": "CRITICAL" if score >= 0.90 else "SUSPICIOUS",
                            }
                        )

        flagged_pairs.sort(key=lambda x: x["similarity_score"], reverse=True)

        return {
            "assessment_id": assessment.id,
            "assessment_title": assessment.title,
            "total_pairs_analyzed": sum(
                len(subs) * (len(subs) - 1) // 2 for subs in problems_map.values()
            ),
            "flagged_cases_count": len(flagged_pairs),
            "flagged_pairs": flagged_pairs,
        }
