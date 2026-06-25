from __future__ import annotations

from collections import defaultdict

from .models import SearchItem, WeeklyReport


def write_weekly_report(items: list[SearchItem], *, week_label: str, revision: int = 0, critic_feedback: list[str] | None = None) -> WeeklyReport:
    grouped: dict[str, list[SearchItem]] = defaultdict(list)
    for item in items:
        grouped[item.competitor].append(item)

    lines: list[str] = []
    lines.append(f"# C&M 압축기 경쟁사 주간 모니터링 리포트 — {week_label}")
    lines.append("")
    lines.append("## 1. 이번 주 핵심 동향, 3줄 요약")
    top_items = items[:3]
    if top_items:
        for item in top_items:
            lines.append(f"- {item.competitor} {item.product}: {item.summary}")
    else:
        lines.append("- 수집된 항목이 없습니다.")
    lines.append("")

    lines.append("## 2. 경쟁사별 신규 정보")
    for competitor, competitor_items in sorted(grouped.items()):
        lines.append(f"### {competitor}")
        for item in competitor_items:
            lines.append(f"- 제품/군: {item.product}")
            lines.append(f"  - 냉매/타입: {item.refrigerant} / {item.compressor_type}")
            lines.append(f"  - 요약: {item.summary}")
            lines.append(f"  - 출처: {item.source_url} ({item.source_date})")
    lines.append("")

    lines.append("## 3. R290 Re Gap 현황 업데이트")
    r290_items = [i for i in items if "R290" in i.refrigerant and "Recip" in i.compressor_type]
    if r290_items:
        for item in r290_items:
            lines.append(f"- {item.competitor} {item.product}: {item.samsung_gap_note or 'Samsung Gap 관점 추가 분석 필요'}")
    else:
        lines.append("- 이번 입력에는 R290 Reciprocating 관련 신규 Gap 항목이 없습니다.")
    lines.append("")

    lines.append("## 4. R454B Sc 벤치마크 변동")
    r454b_items = [i for i in items if "R454B" in i.refrigerant and ("Scroll" in i.compressor_type or "Sc" in i.compressor_type)]
    if r454b_items:
        for item in r454b_items:
            lines.append(f"- {item.competitor} {item.product}: {item.samsung_gap_note or '조건 정규화 후 성능 비교 필요'}")
    else:
        lines.append("- 이번 입력에는 R454B Scroll 관련 신규 벤치마크 항목이 없습니다.")
    lines.append("")

    lines.append("## 5. 주목할 특허·기술")
    patent_like = [i for i in items if "patent" in i.source_url.lower() or "특허" in i.summary]
    if patent_like:
        for item in patent_like:
            lines.append(f"- {item.competitor}: {item.summary} / 출처: {item.source_url}")
    else:
        lines.append("- 특허/논문성 항목은 별도 Search Agent 연결 후 보강 필요합니다.")
    lines.append("")

    lines.append("## 6. 다음 주 모니터링 포인트")
    lines.append("- R290 Re: Embraco/Nidec, Secop, GMCC의 신규 모델명과 효율 등급 변화 확인")
    lines.append("- R454B Sc: GMCC, Danfoss, LG, Copeland의 조건 정규화 가능한 성능 데이터 확보")
    lines.append("- Highly: Rotary 중심 별도 트래킹 유지")
    if critic_feedback:
        lines.append("- Critic 피드백 반영 사항: " + "; ".join(critic_feedback))
    lines.append("")

    return WeeklyReport(
        title=f"C&M 압축기 경쟁사 주간 모니터링 리포트 — {week_label}",
        markdown="\n".join(lines),
        items=items,
        revision=revision,
    )
