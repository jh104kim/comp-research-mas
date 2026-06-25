from __future__ import annotations

from .models import CriticReview, WeeklyReport

REQUIRED_COMPETITORS = {"Embraco", "Nidec", "Secop", "GMCC", "Danfoss", "LG", "Copeland", "Highly"}


def review_report(report: WeeklyReport) -> CriticReview:
    markdown = report.markdown
    findings: list[str] = []
    fixes: list[str] = []
    score = 100

    if "출처:" not in markdown or "http" not in markdown:
        score -= 25
        fixes.append("각 신규 정보에 출처 URL과 날짜를 명시하세요.")
    else:
        findings.append("출처 URL 섹션이 포함되어 있습니다.")

    present = {item.competitor for item in report.items}
    missing = sorted(c for c in REQUIRED_COMPETITORS if c not in present)
    if missing:
        score -= min(25, 3 * len(missing))
        fixes.append("누락 모니터링 대상 확인: " + ", ".join(missing))
    else:
        findings.append("핵심 경쟁사 커버리지가 충족되었습니다.")

    if "Samsung Gap" not in markdown and "Gap" not in markdown:
        score -= 25
        fixes.append("Samsung Gap 관점의 비교/해석을 별도 섹션으로 보강하세요.")
    else:
        findings.append("Samsung Gap 관점 섹션이 포함되어 있습니다.")

    wordish_count = len(markdown.split())
    if wordish_count < 180:
        score -= 15
        fixes.append("리포트 분량이 너무 짧습니다. 경쟁사별 신규 정보와 다음 액션을 보강하세요.")
    elif wordish_count > 1800:
        score -= 10
        fixes.append("리포트가 너무 깁니다. A4 1~2장 수준으로 압축하세요.")
    else:
        findings.append("분량은 MVP 기준 허용 범위입니다.")

    score = max(0, score)
    return CriticReview(score=score, passed=score >= 80, findings=findings, required_fixes=fixes)
