from __future__ import annotations

import html
from datetime import datetime
from typing import Any

AIRBNB_RED = "#FF5A5F"
MEDIUM = "#FFB400"
SAFE = "#008489"
LINE = "#EBEBEB"


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _badge(label: str, level: str = "none") -> str:
    colors = {
        "high": (AIRBNB_RED, "#FFFFFF"),
        "medium": (MEDIUM, "#FFFFFF"),
        "low": (SAFE, "#FFFFFF"),
        "none": ("#EBEBEB", "#717171"),
        "보유": (SAFE, "#FFFFFF"),
        "미보유": (AIRBNB_RED, "#FFFFFF"),
        "대응중": (MEDIUM, "#FFFFFF"),
        "확인필요": ("#EBEBEB", "#717171"),
    }
    bg, fg = colors.get(level, colors.get(label, ("#EBEBEB", "#717171")))
    return f'<span class="badge" style="background:{bg};color:{fg}">{_esc(label)}</span>'


def _section_from_markdown(draft: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in draft:
        return ""
    rest = draft.split(marker, 1)[1]
    end = rest.find("\n## ")
    section = rest if end == -1 else rest[:end]
    return section.strip()


def _markdown_lines_to_html(text: str) -> str:
    rows: list[str] = []
    in_ul = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line == "---":
            continue
        if line.startswith("### "):
            if in_ul:
                rows.append("</ul>")
                in_ul = False
            rows.append(f"<h3>{_esc(line[4:])}</h3>")
        elif line.startswith("#### "):
            if in_ul:
                rows.append("</ul>")
                in_ul = False
            rows.append(f"<h4>{_esc(line[5:])}</h4>")
        elif line.startswith("- "):
            if not in_ul:
                rows.append("<ul>")
                in_ul = True
            rows.append(f"<li>{_inline_format(line[2:])}</li>")
        else:
            if in_ul:
                rows.append("</ul>")
                in_ul = False
            rows.append(f"<p>{_inline_format(line)}</p>")
    if in_ul:
        rows.append("</ul>")
    return "\n".join(rows)


def _inline_format(text: str) -> str:
    escaped = _esc(text)
    for level in ("high", "medium", "low", "none"):
        escaped = escaped.replace(level, _badge(level, level))
    return escaped


def _gap_table(state: dict[str, Any]) -> str:
    bundle = state.get("analysis_bundle") or {}
    rows: list[str] = []
    for threat in bundle.get("threat_summary", []):
        level = threat.get("threat_level", "none")
        rows.append(
            f'<tr class="threat-{_esc(level)}">'
            f'<td>{_esc(threat.get("compressor_type"))}</td>'
            f'<td>{_esc(threat.get("condition"))}</td>'
            f'<td>{_esc(threat.get("refrigerant"))}</td>'
            f'<td>{_esc(threat.get("competitor"))}</td>'
            f'<td>{_badge(level, level)}</td>'
            f'<td>{_esc(threat.get("trust_score"))}</td>'
            "</tr>"
        )
    if not rows:
        for item in state.get("evidence", []):
            level = item.get("threat_level", "none")
            rows.append(
                f'<tr class="threat-{_esc(level)}">'
                f'<td>{_esc(item.get("compressor_type"))}</td>'
                f'<td>{_esc(item.get("condition_or_capacity"))}</td>'
                f'<td>{_esc("/".join(item.get("refrigerant", [])))}</td>'
                f'<td>{_esc(item.get("competitor"))}</td>'
                f'<td>{_badge(level, level)}</td>'
                f'<td>{_esc(item.get("trust_score"))}</td>'
                "</tr>"
            )
    body = "\n".join(rows) or '<tr><td colspan="6">확인된 Gap 항목 없음</td></tr>'
    return f"""
<table class="gap-table">
  <thead><tr><th>타입</th><th>조건/구간</th><th>냉매</th><th>경쟁사</th><th>위협도</th><th>신뢰도</th></tr></thead>
  <tbody>{body}</tbody>
</table>
"""


def _type_sections(state: dict[str, Any]) -> str:
    evidence = state.get("evidence", [])
    cards: list[str] = []
    type_labels = {"Re": "Reciprocating", "Ro": "Rotary", "Sc": "Scroll"}
    categories = ["신냉매·냉매전환", "성능·효율", "신제품·라인업", "신뢰성·내구성", "특허·기술", "규격·인증", "가격·유통", "전시회·발표"]
    for ctype, label in type_labels.items():
        type_items = [item for item in evidence if item.get("compressor_type") == ctype]
        category_blocks: list[str] = []
        for category in categories:
            items = [item for item in type_items if item.get("category") == category]
            item_html = "".join(
                f"""
<div class="competitor-item threat-{_esc(item.get('threat_level', 'none'))}">
  <div class="item-title">{_esc(item.get('competitor'))} {_badge(item.get('threat_level', 'none'), item.get('threat_level', 'none'))}</div>
  <p>{_esc(item.get('raw_text') or item.get('summary'))}</p>
  <p>삼성 비교 관점: {_badge(item.get('samsung_status'), item.get('samsung_status'))} · 출처: {_esc(item.get('source_name'))} / {_esc(item.get('source_date'))}</p>
</div>
"""
                for item in items
            ) or '<p class="muted">해당 없음 — 이번 달 확인된 고신뢰 근거 없음</p>'
            category_blocks.append(f"<details><summary>{_esc(category)}</summary>{item_html}</details>")
        cards.append(f"""
<section class="card type-card" id="{ctype}">
  <h2>{ctype} <span>{_esc(label)}</span></h2>
  {''.join(category_blocks)}
</section>
""")
    return "\n".join(cards)


def _sources_html(state: dict[str, Any]) -> str:
    sources = state.get("sources", [])
    if not sources:
        return "<p>출처 없음</p>"
    return "<ul>" + "".join(f'<li><a href="{_esc(s.get("source_url"))}">{_esc(s.get("source_name"))}</a> · {_esc(s.get("source_date"))} · {_esc(s.get("source_type"))}</li>' for s in sources) + "</ul>"


def markdown_to_html(draft: str, state: dict[str, Any]) -> str:
    period_id = state.get("period_id", "unknown")
    meta = state.get("report_meta") or {}
    if not meta and isinstance(state.get("analysis_bundle"), dict):
        bundle = state["analysis_bundle"]
        meta = {
            "total_evidence_count": len(state.get("evidence", [])),
            "high_threat_count": sum(1 for item in bundle.get("threat_summary", []) if item.get("threat_level") == "high"),
            "signal_count": len(bundle.get("new_signals", [])),
        }
    title = draft.splitlines()[0].replace("#", "").strip() if draft else "압축기 경쟁사 월간 모니터링 리포트"
    summary = _section_from_markdown(draft, "이번 달 핵심 동향 요약") or _section_from_markdown(draft, "이번 주 핵심 동향 요약")
    monitoring = _section_from_markdown(draft, "다음 달 모니터링 포인트")
    auto = state.get("auto_approve_result", {}).get("audit_log", {})
    auto_text = "충족" if auto.get("approve") else "미충족/미평가"
    generated_at = datetime.now().isoformat(timespec="seconds")
    css = f"""
<style>
:root{{--airbnb-red:{AIRBNB_RED};--medium:{MEDIUM};--safe:{SAFE};--line:{LINE};--text:#222222;}}
*{{box-sizing:border-box}} body{{margin:0;background:#FFFFFF;color:var(--text);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.55;}}
.container{{max-width:960px;margin:0 auto;padding:32px 20px 56px;}}
.hero{{background:var(--airbnb-red);color:#fff;border-radius:0 0 24px 24px;padding:42px 32px;margin-bottom:32px;}}
.hero h1{{margin:0 0 12px;font-size:34px;letter-spacing:-0.03em;}}
.pill{{display:inline-block;border-radius:999px;background:rgba(255,255,255,.18);padding:8px 14px;font-weight:700;}}
.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:24px;}}
.metric{{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.3);border-radius:16px;padding:16px;}}
.metric strong{{display:block;font-size:28px;}}
.card{{border:1px solid var(--line);border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);padding:24px;margin:0 0 32px;background:#fff;}}
h2{{margin-top:0;font-size:24px;letter-spacing:-0.02em;}} h2 span{{color:#717171;font-weight:500;font-size:16px;}}
ul{{padding-left:22px}} .muted{{color:#717171;}}
.badge{{display:inline-block;border-radius:999px;padding:3px 9px;font-size:12px;font-weight:700;vertical-align:middle;}}
.tabs{{display:flex;gap:8px;margin-bottom:16px;}} .tab{{border:1px solid var(--line);border-radius:999px;padding:8px 14px;text-decoration:none;color:#222;font-weight:700;}}
details{{border-top:1px solid var(--line);padding:14px 0;}} summary{{cursor:pointer;font-weight:800;}}
.competitor-item{{border-radius:12px;padding:14px 16px;margin:12px 0;background:#FAFAFA;border-left:4px solid var(--line);}}
.competitor-item.threat-high{{background:#FFF0F0;border-left-color:var(--airbnb-red);}}
.competitor-item.threat-medium{{background:#FFFBF0;border-left-color:var(--medium);}}
.item-title{{font-weight:800;margin-bottom:6px;}}
.gap-table{{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden;border:1px solid var(--line);border-radius:12px;}}
th{{background:#F7F7F7;text-align:left;padding:12px;border-bottom:1px solid var(--line);}}td{{padding:12px;border-bottom:1px solid var(--line);}}tr:hover{{background:#FAFAFA;}}
tr.threat-high td{{background:#FFF0F0;border-left:4px solid var(--airbnb-red);}}tr.threat-medium td{{background:#FFFBF0;}}
.sources{{background:#F7F7F7;}} footer{{color:#717171;text-align:center;border-top:1px solid var(--line);padding-top:24px;margin-top:32px;font-size:13px;}}
@media(max-width:720px){{.metrics{{grid-template-columns:1fr}}.hero{{border-radius:0 0 18px 18px}}}}
</style>
"""
    return f"""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{css}<title>{_esc(title)}</title></head>
<body>
  <header class="hero">
    <div class="container" style="padding-top:0;padding-bottom:0">
      <h1>{_esc(title)}</h1>
      <span class="pill">기간 { _esc(period_id) }</span>
      <div class="metrics">
        <div class="metric"><span>Evidence</span><strong>{_esc(meta.get('total_evidence_count', len(state.get('evidence', []))))}</strong></div>
        <div class="metric"><span>High threat</span><strong>{_esc(meta.get('high_threat_count', 0))}</strong></div>
        <div class="metric"><span>Signals</span><strong>{_esc(meta.get('signal_count', 0))}</strong></div>
      </div>
    </div>
  </header>
  <main class="container">
    <section class="card"><h2>이번 달 핵심 동향</h2>{_markdown_lines_to_html(summary)}</section>
    <nav class="tabs"><a class="tab" href="#Re">Re</a><a class="tab" href="#Ro">Ro</a><a class="tab" href="#Sc">Sc</a></nav>
    {_type_sections(state)}
    <section class="card"><h2>삼성 Gap 종합 현황</h2>{_gap_table(state)}</section>
    <section class="card"><h2>다음 달 모니터링 포인트</h2>{_markdown_lines_to_html(monitoring)}</section>
    <section class="card sources"><h2>출처 목록</h2>{_sources_html(state)}</section>
    <footer>생성일시: {_esc(generated_at)} · auto_approve 조건: {_esc(auto_text)} · score={_esc(state.get('score', ''))}, hard_fail={_esc(state.get('hard_fail', False))}, guardian={_esc((state.get('guardian_result') or {}).get('severity', 'unknown'))}</footer>
  </main>
</body>
</html>
"""
