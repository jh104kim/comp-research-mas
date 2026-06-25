from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .report_html import _badge, _css, _esc, _js

PERIODS_H2_2025 = [f"2025-{m:02d}" for m in range(7, 13)]
PERIODS_H1_2026 = [f"2026-{m:02d}" for m in range(1, 7)]
PERIOD_GROUPS = {"2025 H2": PERIODS_H2_2025, "2026 H1": PERIODS_H1_2026}
COMPRESSOR_LABELS = {"Re": "왕복동(Reciprocating)", "Ro": "로터리(Rotary)", "Sc": "스크롤(Scroll)"}
PRIMARY_FOCUS = {
    "Re": ["GMCC/Midea", "LG", "Embraco/Nidec", "Secop"],
    "Ro": ["GMCC/Midea", "LG", "Highly", "Panasonic"],
    "Sc": ["Copeland/Emerson", "Danfoss", "LG", "GMCC/Midea"],
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _safe_refs(item: dict[str, Any]) -> list[str]:
    refs = item.get("refrigerant") or item.get("refrigerants") or []
    if isinstance(refs, str):
        return [refs]
    return [str(r) for r in refs if r]


def _period_evidence(period: str, base: Path) -> list[dict[str, Any]]:
    data = _load_json(base / f"outputs/evidence/{period}_evidence.json")
    evidence = list(data.get("evidence", []))
    for item in evidence:
        item.setdefault("period_id", period)
    return evidence


def load_special_dataset(base: str | Path = ".") -> dict[str, Any]:
    root = Path(base)
    groups: dict[str, list[dict[str, Any]]] = {}
    for group, periods in PERIOD_GROUPS.items():
        rows: list[dict[str, Any]] = []
        for period in periods:
            rows.extend(_period_evidence(period, root))
        groups[group] = rows
    all_rows = [item for rows in groups.values() for item in rows]
    return {"groups": groups, "evidence": all_rows, "generated_at": datetime.now().isoformat(timespec="seconds")}


def _count_by(rows: list[dict[str, Any]], key: str) -> Counter[str]:
    return Counter(str(item.get(key) or "확인필요") for item in rows)


def _count_refs(rows: list[dict[str, Any]]) -> Counter[str]:
    c: Counter[str] = Counter()
    for item in rows:
        for ref in _safe_refs(item):
            c[ref] += 1
    return c


def _source_link(item: dict[str, Any]) -> str:
    url = str(item.get("source_url") or "")
    label = item.get("source_name") or item.get("title") or item.get("source_type") or url or "출처"
    if url.startswith(("http://", "https://")):
        return f'<a href="{_esc(url)}" target="_blank" rel="noopener">{_esc(label)}</a>'
    return _esc(label)


def _period_table(dataset: dict[str, Any]) -> str:
    rows = []
    for group, periods in PERIOD_GROUPS.items():
        for period in periods:
            count = sum(1 for item in dataset["groups"][group] if item.get("period_id") == period)
            rows.append(f"<tr><td>{_esc(group)}</td><td>{_esc(period)}</td><td><strong>{count}</strong></td></tr>")
    return f'<section class="card"><h2>월별 수집 건수</h2><table><thead><tr><th>구간</th><th>월</th><th>Evidence 건수</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>'


def _summary_cards(dataset: dict[str, Any]) -> str:
    all_rows = dataset["evidence"]
    group_cards = []
    for group, rows in dataset["groups"].items():
        group_cards.append(f'<div class="kpi-card"><span>{_esc(group)}</span><strong>{len(rows)}</strong><span class="delta">evidence</span></div>')
    kpis = [
        ("총 Evidence", len(all_rows)),
        ("경쟁사 수", len(_count_by(all_rows, "competitor"))),
        ("출처 URL 수", len({item.get("source_url") for item in all_rows if item.get("source_url")})),
        ("High Threat", sum(1 for item in all_rows if item.get("threat_level") == "high")),
    ]
    cards = "".join(f'<div class="kpi-card {"high" if label == "High Threat" and value else ""}"><span>{_esc(label)}</span><strong>{_esc(value)}</strong><span class="delta">2025 H2 + 2026 H1</span></div>' for label, value in kpis)
    return f'<section class="kpi-grid">{"".join(group_cards)}{cards}</section>'


def _comparison_tables(dataset: dict[str, Any]) -> str:
    def table(title: str, key: str) -> str:
        headers = []
        body_rows = []
        keys = sorted({k for rows in dataset["groups"].values() for k in _count_by(rows, key).keys()})
        for group in PERIOD_GROUPS:
            headers.append(f"<th>{_esc(group)}</th>")
        for name in keys:
            cells = []
            for group, rows in dataset["groups"].items():
                cells.append(f"<td>{_count_by(rows, key).get(name, 0)}</td>")
            body_rows.append(f"<tr><td>{_esc(name)}</td>{''.join(cells)}</tr>")
        return f'<section class="card"><h2>{_esc(title)}</h2><table><thead><tr><th>구분</th>{"".join(headers)}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></section>'
    refs_rows = []
    refs = sorted({r for rows in dataset["groups"].values() for r in _count_refs(rows)})
    for ref in refs:
        refs_rows.append(f'<tr><td>{_esc(ref)}</td><td>{_count_refs(dataset["groups"]["2025 H2"]).get(ref,0)}</td><td>{_count_refs(dataset["groups"]["2026 H1"]).get(ref,0)}</td></tr>')
    return table("경쟁사별 수집 건수", "competitor") + table("압축기별 수집 건수", "compressor_type") + table("카테고리별 수집 건수", "category") + f'<section class="card"><h2>냉매별 수집 건수</h2><table><thead><tr><th>냉매</th><th>2025 H2</th><th>2026 H1</th></tr></thead><tbody>{"".join(refs_rows)}</tbody></table></section>'


def _top_sources(rows: list[dict[str, Any]], limit: int = 18) -> list[dict[str, Any]]:
    by_url: dict[str, dict[str, Any]] = {}
    for item in rows:
        url = str(item.get("source_url") or "")
        if not url:
            continue
        current = by_url.setdefault(url, {"item": item, "count": 0, "periods": set(), "competitors": set(), "types": set()})
        current["count"] += 1
        current["periods"].add(item.get("period_id"))
        current["competitors"].add(item.get("competitor"))
        current["types"].add(item.get("compressor_type"))
    rows2 = sorted(by_url.values(), key=lambda x: (x["count"], max([x["item"].get("trust_score", 0)])), reverse=True)[:limit]
    return rows2


def _insights(dataset: dict[str, Any]) -> str:
    rows = dataset["evidence"]
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in rows:
        by_type[str(item.get("compressor_type") or "확인필요")].append(item)
    cards = []
    for ctype in ["Re", "Ro", "Sc"]:
        items = by_type.get(ctype, [])
        comp = _count_by(items, "competitor")
        cats = _count_by(items, "category")
        refs = _count_refs(items)
        high = [i for i in items if i.get("threat_level") == "high"]
        focus = [name for name in PRIMARY_FOCUS.get(ctype, []) if comp.get(name)]
        if ctype == "Re":
            insight = "R290/R600a 자연냉매 축이 반복적으로 포착된다. 삼성은 소형·상업용 Re에서 R290 라인업/인증/안전 설계 readiness를 우선 점검해야 한다."
        elif ctype == "Ro":
            insight = "LG·GMCC/Midea 중심의 Ro/R32·R290 신호가 누적된다. 삼성은 인버터 효율과 냉매 전환을 묶은 중기 대응 포트폴리오가 필요하다."
        else:
            insight = "Copeland/Danfoss의 R454B·히트펌프 축이 Sc의 핵심 압력이다. 삼성은 A2L/R454B 스크롤 대응과 북미·유럽 규제/전시 시그널을 별도 P1 과제로 둬야 한다."
        cards.append(f"""
<section class="card samsung-insight">
  <h2>{_esc(ctype)} · {_esc(COMPRESSOR_LABELS.get(ctype, ctype))} 삼성 인사이트</h2>
  <div class="grid-3">
    <div><h3>수집 규모</h3><p><strong>{len(items)}</strong>건 / high threat {len(high)}건</p></div>
    <div><h3>주요 경쟁사</h3><p>{_esc(', '.join(focus or [name for name,_ in comp.most_common(4)]))}</p></div>
    <div><h3>주요 냉매</h3><p>{_esc(', '.join([r for r,_ in refs.most_common(5)]))}</p></div>
  </div>
  <ul>
    <li>최다 카테고리: {_esc(', '.join([f'{k} {v}건' for k,v in cats.most_common(3)]))}</li>
    <li>{_esc(insight)}</li>
    <li>권장: 공식 출처/특허/규제 근거를 분리해 삼성 제품기획 Gap Matrix의 우선순위를 재점검</li>
  </ul>
</section>
""")
    return "".join(cards)


def _category_insights(dataset: dict[str, Any]) -> str:
    rows = dataset["evidence"]
    cats = _count_by(rows, "category")
    lines = []
    for cat, count in cats.most_common():
        items = [i for i in rows if i.get("category") == cat]
        comps = ", ".join([k for k, _ in _count_by(items, "competitor").most_common(4)])
        refs = ", ".join([k for k, _ in _count_refs(items).most_common(4)])
        if "냉매" in cat:
            msg = "냉매 전환은 전 타입 공통 축이며, R290/R454B/R32 중심으로 삼성 로드맵 대비가 필요"
        elif "특허" in cat:
            msg = "특허/기술 근거는 직접 제품 출시보다 선행 신호로 취급하고 FTO/회피설계 리뷰 필요"
        elif "규격" in cat:
            msg = "규제/인증은 북미 EPA SNAP 및 EU F-Gas 흐름과 연결해 A2L/자연냉매 허용 범위 확인 필요"
        elif "전시" in cat:
            msg = "전시회 발표는 다음 공식 제품 발표의 조기 신호로 모니터링 가치가 큼"
        else:
            msg = "경쟁사 공식 라인업/성능 근거와 교차 검증해 삼성 대응 우선순위화 필요"
        lines.append(f"<tr><td>{_esc(cat)}</td><td>{count}</td><td>{_esc(comps)}</td><td>{_esc(refs)}</td><td>{_esc(msg)}</td></tr>")
    return f'<section class="card category-insight"><h2>카테고리별 분석</h2><table><thead><tr><th>카테고리</th><th>건수</th><th>주요 경쟁사</th><th>주요 냉매</th><th>삼성 관점</th></tr></thead><tbody>{"".join(lines)}</tbody></table></section>'


def _source_section(dataset: dict[str, Any]) -> str:
    rows = []
    for rec in _top_sources(dataset["evidence"], limit=30):
        item = rec["item"]
        rows.append(
            f'<tr><td>{_source_link(item)}</td><td>{_esc(item.get("source_type"))}</td><td>{_esc(item.get("trust_score"))}</td><td>{rec["count"]}</td><td>{_esc(", ".join(sorted(rec["periods"])))}</td><td>{_esc(", ".join(sorted(rec["competitors"])))}</td><td>{_esc(", ".join(sorted(rec["types"])))}</td></tr>'
        )
    return f'<section class="card footer-sources"><h2>주요 자료 출처 및 링크</h2><table><thead><tr><th>출처</th><th>유형</th><th>신뢰도</th><th>사용건수</th><th>기간</th><th>경쟁사</th><th>타입</th></tr></thead><tbody>{"".join(rows)}</tbody></table><p class="muted">※ 본 특별 리포트는 repo에 누적된 whitelist 기반 title/summary evidence를 집계한 분석입니다. 상세 원문/전문 해석은 링크별 공식 문서 확인이 필요합니다.</p></section>'


def build_markdown(dataset: dict[str, Any]) -> str:
    all_rows = dataset["evidence"]
    lines = [
        "# 2026년 기준 압축기 경쟁사 특별 리포트",
        "",
        f"생성일: {dataset['generated_at']}",
        "분석 범위: 2025년 하반기(7~12월) vs 2026년 상반기(1~6월)",
        f"총 evidence: {len(all_rows)}건",
        "",
        "## 1. 구간별 수집 건수",
    ]
    for group, rows in dataset["groups"].items():
        lines.append(f"- {group}: {len(rows)}건")
    lines += ["", "## 2. 압축기별 삼성 인사이트"]
    for ctype in ["Re", "Ro", "Sc"]:
        items = [i for i in all_rows if i.get("compressor_type") == ctype]
        refs = ", ".join([k for k, _ in _count_refs(items).most_common(5)])
        comps = ", ".join([k for k, _ in _count_by(items, "competitor").most_common(5)])
        lines.append(f"- {ctype}({COMPRESSOR_LABELS[ctype]}): {len(items)}건. 주요 경쟁사 {comps}. 주요 냉매 {refs}.")
    lines += ["", "## 3. 주요 출처"]
    for rec in _top_sources(all_rows, limit=20):
        item = rec["item"]
        lines.append(f"- {item.get('source_name') or item.get('source_type')} ({rec['count']}건): {item.get('source_url')}")
    lines += ["", "## 4. 실행 방법", "", "```bash", "uv sync --extra test", "uv run python -m comp_research_mas.cli build-special-report --send-email", "```"]
    return "\n".join(lines) + "\n"


def build_html(dataset: dict[str, Any]) -> str:
    title = "2026년 기준 압축기 경쟁사 특별 리포트"
    generated = dataset["generated_at"]
    return f"""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{_css()}<title>{_esc(title)}</title></head>
<body>
  <header class="hero"><div class="container"><h1>{_esc(title)}</h1><div class="hero-meta"><span class="pill">2025 H2 vs 2026 H1</span><span class="pill">생성 {_esc(generated)}</span><span class="pill">Evidence {_esc(len(dataset['evidence']))}건</span><span class="pill">기준 2026년 현재</span></div></div></header>
  <main class="container">
    {_summary_cards(dataset)}
    <section class="card samsung-insight"><h2>Executive Summary</h2><ul><li>2025년 하반기와 2026년 상반기 모두 월별 수집 데이터가 존재하며, 2026년 기준 누적 Gap Matrix의 핵심 축은 자연냉매 R290, A2L/R454B, R32 전환이다.</li><li>Re는 GMCC/Midea·LG·Embraco/Secop 계열의 자연냉매 대응이 반복 포착되어 삼성의 R290 안전/인증/라인업 readiness 점검이 필요하다.</li><li>Ro는 LG·GMCC/Midea의 R32/R290 및 인버터 효율 신호가 중심이므로, 효율·냉매 전환을 묶은 중기 대응 과제가 필요하다.</li><li>Sc는 Copeland/Danfoss의 R454B/A2L 및 히트펌프 축이 중요하며 북미·유럽 규제와 전시회 신호를 함께 봐야 한다.</li></ul></section>
    {_period_table(dataset)}
    {_comparison_tables(dataset)}
    {_insights(dataset)}
    {_category_insights(dataset)}
    {_source_section(dataset)}
  </main>{_js()}
</body></html>"""


def generate_special_report(base: str | Path = ".") -> dict[str, Any]:
    root = Path(base)
    dataset = load_special_dataset(root)
    out_dir = root / "outputs/reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "2026-special-competitor-insight-report.md"
    html_path = out_dir / "2026-special-competitor-insight-report.html"
    json_path = root / "outputs/analysis/2026_special_report_summary.json"
    md_path.write_text(build_markdown(dataset), encoding="utf-8")
    html_path.write_text(build_html(dataset), encoding="utf-8")
    summary = {
        "generated_at": dataset["generated_at"],
        "period_groups": {group: periods for group, periods in PERIOD_GROUPS.items()},
        "counts": {group: len(rows) for group, rows in dataset["groups"].items()},
        "total_evidence": len(dataset["evidence"]),
        "by_competitor": dict(_count_by(dataset["evidence"], "competitor")),
        "by_compressor_type": dict(_count_by(dataset["evidence"], "compressor_type")),
        "by_category": dict(_count_by(dataset["evidence"], "category")),
        "by_refrigerant": dict(_count_refs(dataset["evidence"])),
        "output_paths": {"md": str(md_path), "html": str(html_path), "summary": str(json_path)},
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
