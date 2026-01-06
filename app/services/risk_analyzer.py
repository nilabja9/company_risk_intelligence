from dataclasses import dataclass
from typing import Any
import json
import uuid

from app.services.snowflake_client import get_snowflake_client
from app.services.claude_client import get_claude_client


@dataclass
class RiskAssessment:
    assessment_id: str
    company_ticker: str
    filing_date: str
    risk_category: str
    risk_score: float  # 0-100
    summary: str
    evidence: list[dict]


class RiskAnalyzer:
    RISK_CATEGORIES = [
        "REGULATORY",
        "LITIGATION",
        "FINANCIAL",
        "OPERATIONAL",
        "MARKET",
        "ACCOUNTING"
    ]

    SEVERITY_SCORES = {
        "LOW": 25,
        "MEDIUM": 50,
        "HIGH": 75,
        "CRITICAL": 100
    }

    # Keywords that may indicate red flags
    RED_FLAG_KEYWORDS = {
        "litigation": [
            "lawsuit", "litigation", "legal proceedings", "plaintiff",
            "defendant", "settlement", "damages", "injunction"
        ],
        "accounting": [
            "restatement", "material weakness", "going concern",
            "auditor change", "internal control deficiency", "irregularities"
        ],
        "financial": [
            "default", "covenant violation", "liquidity concerns",
            "credit downgrade", "impairment", "write-off"
        ],
        "regulatory": [
            "investigation", "subpoena", "SEC inquiry", "DOJ",
            "enforcement action", "consent decree", "penalty"
        ]
    }

    def __init__(self):
        self.snowflake = get_snowflake_client()
        self.claude = get_claude_client()

    def analyze_risks(
        self,
        filing_text: str,
        company_ticker: str,
        company_name: str,
        filing_date: str
    ) -> list[RiskAssessment]:
        # Get Claude's risk analysis
        analysis = self.claude.analyze_risks(filing_text, company_name)
        risks = analysis.get("risks", [])

        # Also do keyword-based detection
        keyword_risks = self._detect_keyword_risks(filing_text)

        # Combine and deduplicate
        all_risks = self._merge_risks(risks, keyword_risks)

        # Create risk assessments
        assessments = []
        for risk in all_risks:
            category = risk.get("category", "OPERATIONAL")
            severity = risk.get("severity", "MEDIUM")

            assessments.append(RiskAssessment(
                assessment_id=f"{company_ticker}_{filing_date}_{category}_{uuid.uuid4().hex[:8]}",
                company_ticker=company_ticker,
                filing_date=filing_date,
                risk_category=category,
                risk_score=self.SEVERITY_SCORES.get(severity, 50),
                summary=risk.get("description", ""),
                evidence=[{
                    "text": risk.get("evidence", ""),
                    "severity": severity
                }]
            ))

        return assessments

    def _detect_keyword_risks(self, text: str) -> list[dict]:
        text_lower = text.lower()
        detected = []

        for category, keywords in self.RED_FLAG_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # Find context around the keyword
                    idx = text_lower.find(keyword.lower())
                    start = max(0, idx - 100)
                    end = min(len(text), idx + 100)
                    context = text[start:end]

                    detected.append({
                        "category": category.upper(),
                        "severity": "MEDIUM",
                        "description": f"Mention of '{keyword}' detected",
                        "evidence": f"...{context}..."
                    })
                    break  # Only one per category per keyword group

        return detected

    def _merge_risks(
        self,
        claude_risks: list[dict],
        keyword_risks: list[dict]
    ) -> list[dict]:
        # Combine, prioritizing Claude's analysis
        seen_categories = set()
        merged = []

        for risk in claude_risks:
            cat = risk.get("category", "").upper()
            if cat not in seen_categories:
                merged.append(risk)
                seen_categories.add(cat)

        for risk in keyword_risks:
            cat = risk.get("category", "").upper()
            if cat not in seen_categories:
                merged.append(risk)
                seen_categories.add(cat)

        return merged

    def compare_risk_sections(
        self,
        current_text: str,
        previous_text: str,
        company_name: str,
        section_name: str
    ) -> dict:
        return self.claude.summarize_changes(
            current_text,
            previous_text,
            section_name,
            company_name
        )

    def calculate_overall_risk_score(self, assessments: list[RiskAssessment]) -> float:
        if not assessments:
            return 0.0

        # Weighted average based on category importance
        weights = {
            "ACCOUNTING": 1.5,
            "FINANCIAL": 1.3,
            "LITIGATION": 1.2,
            "REGULATORY": 1.1,
            "OPERATIONAL": 1.0,
            "MARKET": 0.9
        }

        total_weight = 0
        weighted_sum = 0

        for assessment in assessments:
            weight = weights.get(assessment.risk_category, 1.0)
            weighted_sum += assessment.risk_score * weight
            total_weight += weight

        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

    def store_assessments(self, assessments: list[RiskAssessment]) -> int:
        stored = 0
        for assessment in assessments:
            query = """
            INSERT INTO risk_assessments
            (assessment_id, company_ticker, filing_date, risk_category,
             risk_score, summary, evidence)
            VALUES (%s, %s, %s, %s, %s, %s, PARSE_JSON(%s))
            """
            try:
                with self.snowflake.get_cursor(dict_cursor=False) as cursor:
                    cursor.execute(query, (
                        assessment.assessment_id,
                        assessment.company_ticker,
                        assessment.filing_date,
                        assessment.risk_category,
                        assessment.risk_score,
                        assessment.summary,
                        json.dumps(assessment.evidence)
                    ))
                stored += 1
            except Exception as e:
                print(f"Error storing assessment {assessment.assessment_id}: {e}")

        return stored

    def get_company_risk_summary(self, ticker: str) -> dict:
        assessments = self.snowflake.get_risk_assessments(ticker)

        if not assessments:
            return {
                "ticker": ticker,
                "overall_score": 0,
                "risk_breakdown": {},
                "recent_flags": []
            }

        # Group by category
        by_category = {}
        recent_flags = []

        for a in assessments:
            cat = a["RISK_CATEGORY"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append({
                "score": a["RISK_SCORE"],
                "summary": a["SUMMARY"],
                "date": str(a["FILING_DATE"])
            })

            if a["RISK_SCORE"] >= 70:
                recent_flags.append({
                    "category": cat,
                    "score": a["RISK_SCORE"],
                    "summary": a["SUMMARY"],
                    "date": str(a["FILING_DATE"])
                })

        # Calculate category averages
        risk_breakdown = {}
        for cat, items in by_category.items():
            avg_score = sum(i["score"] for i in items) / len(items)
            risk_breakdown[cat] = {
                "average_score": round(avg_score, 1),
                "count": len(items),
                "latest": items[0] if items else None
            }

        # Overall score
        all_scores = [a["RISK_SCORE"] for a in assessments]
        overall_score = sum(all_scores) / len(all_scores) if all_scores else 0

        return {
            "ticker": ticker,
            "overall_score": round(overall_score, 1),
            "risk_breakdown": risk_breakdown,
            "recent_flags": recent_flags[:5]  # Top 5 recent flags
        }


def get_risk_analyzer() -> RiskAnalyzer:
    return RiskAnalyzer()
