from __future__ import annotations

from models import Finding, Scorecard, TopWin

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_report(findings: list[Finding]) -> Scorecard:
    """Build a scorecard from a list of findings."""
    if not findings:
        return Scorecard()

    # Sort findings by impact (cost_reduction as primary key)
    ranked_findings = sorted(
        findings,
        key=lambda f: SEVERITY_ORDER.get(f.impact.cost_reduction, 2),
    )

    # Count by category
    by_category: dict[str, int] = {}
    for f in ranked_findings:
        key = f.category.value
        by_category[key] = by_category.get(key, 0) + 1

    # Count by cost impact
    by_impact: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for f in ranked_findings:
        by_impact[f.impact.cost_reduction] = by_impact.get(f.impact.cost_reduction, 0) + 1

    # Top 3 wins (highest impact findings)
    top_wins = [
        TopWin(
            title=f.recommendation.title,
            category=f.category,
            estimated_savings=f.impact.estimated_savings_detail or "See details",
        )
        for f in ranked_findings[:3]
    ]

    # Aggregate savings estimate
    high_count = by_impact.get("high", 0)
    medium_count = by_impact.get("medium", 0)
    if high_count >= 2:
        estimated_total = "Significant cost reduction potential (50%+ on some operations)"
    elif high_count >= 1 or medium_count >= 2:
        estimated_total = "Moderate cost reduction potential (20-50% on key operations)"
    else:
        estimated_total = "Incremental cost savings across multiple areas"

    return Scorecard(
        total_findings=len(findings),
        by_category=by_category,
        by_impact=by_impact,
        estimated_total_savings=estimated_total,
        top_wins=top_wins,
    )
