from __future__ import annotations

import html
import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from .config import flatten_source_whitelist
from .models import CATEGORIES, PRIMARY_COMPETITORS, SECONDARY_COMPETITORS, TYPE_LABELS

AIRBNB_RED = "#FF5A5F"
MEDIUM = "#FFB400"
SAFE = "#008489"
LINE = "#EBEBEB"
CARD_BG = "#F7F7F7"
SAMSUNG_BLUE = "#0070C0"
CATEGORY_PURPLE = "#6B46C1"
TEXT = "#222222"

THREAT_ORDER = {"high": 0, "medium": 1, "low": 2, "none": 3, "": 4}


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value).strip("-")


def _badge(label: Any, level: str | None = None, *, cls: str = "") -> str:
    label_s = str(label if label is not None else "")
    key = level or label_s
    colors = {
        "high": (AIRBNB_RED, "#FFFFFF"),
        "medium": (MEDIUM, "#222222"),
        "low": (SAFE, "#FFFFFF"),
        "none": ("#EBEBEB", "#717171"),
        "보유": (SAFE, "#FFFFFF"),
        "미보유": (AIRBNB_RED, "#FFFFFF"),
        "대응중": (MEDIUM, "#222222"),
        "대응 중": (MEDIUM, "#222222"),
        "확인필요": ("#EBEBEB", "#717171"),
        "확인 필요": ("#EBEBEB", "#717171"),
        "data_insufficient": ("#DDDDDD", "#555555"),
        "official": (SAMSUNG_BLUE, "#FFFFFF"),
        "patent": (CATEGORY_PURPLE, "#FFFFFF"),
        "academic": (SAFE, "#FFFFFF"),
        "exhibition": (AIRBNB_RED, "#FFFFFF"),
        "trade_media": (MEDIUM, "#222222"),
        "news": ("#DDDDDD", "#555555"),
    }
    bg, fg = colors.get(key, ("#EBEBEB", "#717171"))
    return f'<span class="badge {cls}" style="background:{bg};color:{fg}">{_esc(label_s)}</span>'


def _threat_class(level: str | None) -> str:
    return f"threat-{level or 'none'}"


def _evidence(state: dict[str, Any]) -> list[dict[str, Any]]:
    return list(state.get("evidence") or [])


def _bundle(state: dict[str, Any]) -> dict[str, Any]:
    return state.get("analysis_bundle") or {}


def _meta(state: dict[str, Any]) -> dict[str, Any]:
    meta = dict(state.get("report_meta") or {})
    evidence = _evidence(state)
    bundle = _bundle(state)
    meta.setdefault("total_evidence_count", len(evidence))
    meta.setdefault("high_threat_count", sum(1 for t in bundle.get("threat_summary", []) if t.get("threat_level") == "high") or sum(1 for e in evidence if e.get("threat_level") == "high"))
    meta.setdefault("signal_count", len(bundle.get("new_signals", [])))
    return meta


def _period_id(state: dict[str, Any]) -> str:
    return str(state.get("period_id") or state.get("week_id") or "unknown")


def _status_label(value: str) -> str:
    return {"대응중": "대응 중", "확인필요": "확인 필요"}.get(value, value)


def _safe_join_refs(item: dict[str, Any]) -> str:
    refs = item.get("refrigerant") or item.get("refrigerants") or []
    if isinstance(refs, str):
        return refs
    return "/".join(str(ref) for ref in refs)


def _primary_competitors() -> set[str]:
    return {name for values in PRIMARY_COMPETITORS.values() for name in values}


def _competitor_order(name: str) -> tuple[int, str]:
    return (0 if name in _primary_competitors() else 1, name)


def _group_by_competitor(evidence: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in evidence:
        grouped[str(item.get("competitor", "확인필요"))].append(item)
    return dict(sorted(grouped.items(), key=lambda kv: _competitor_order(kv[0])))


def _group_by_category(evidence: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {cat: [] for cat in CATEGORIES}
    for item in evidence:
        grouped.setdefault(str(item.get("category", "기타")), []).append(item)
    return grouped


def _flatten_gap_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    bundle = _bundle(state)
    rows: list[dict[str, Any]] = []
    for ctype, refs in (bundle.get("gap_matrix") or {}).items():
        if not isinstance(refs, dict):
            continue
        for ref, node in refs.items():
            if not isinstance(node, dict):
                continue
            cells = {"default": node} if "samsung" in node or "samsung_status" in node else node
            for condition, cell in cells.items():
                if not isinstance(cell, dict):
                    continue
                competitors = cell.get("competitors", [])
                level = cell.get("threat_level", "none")
                rows.append({
                    "compressor_type": ctype,
                    "refrigerant": ref,
                    "condition": condition,
                    "threat_level": level,
                    "competitors": competitors,
                    "competitor_names": ", ".join(c.get("name", "") for c in competitors if isinstance(c, dict)),
                    "samsung_status": cell.get("samsung_status") or cell.get("samsung") or "확인필요",
                    "period_evidence_quality": cell.get("period_evidence_quality", "sufficient"),
                    "confidence_note": cell.get("confidence_note", ""),
                })
    if rows:
        return sorted(rows, key=lambda r: (THREAT_ORDER.get(r.get("threat_level", "none"), 9), r.get("compressor_type", ""), r.get("refrigerant", "")))
    for item in _evidence(state):
        rows.append({
            "compressor_type": item.get("compressor_type"),
            "refrigerant": _safe_join_refs(item),
            "condition": item.get("condition_or_capacity", "확인필요"),
            "threat_level": item.get("threat_level", "none"),
            "competitors": [{"name": item.get("competitor"), "trust_score": item.get("trust_score"), "source": item.get("source_url")}],
            "competitor_names": item.get("competitor"),
            "samsung_status": item.get("samsung_status", "확인필요"),
            "period_evidence_quality": item.get("period_evidence_quality", "sufficient"),
            "confidence_note": "데이터 부족 period 기반" if item.get("period_evidence_quality") == "data_insufficient" else "",
        })
    return sorted(rows, key=lambda r: THREAT_ORDER.get(r.get("threat_level", "none"), 9))


def _recommended_action(status: str, threat: str) -> tuple[str, str]:
    if status == "미보유" and threat == "high":
        return "즉시 라인업 검토", "P0"
    if status == "미보유" and threat == "medium":
        return "6개월 내 대응 계획", "P1"
    if status in {"대응중", "대응 중"} and threat in {"medium", "high"}:
        return "진행 상황 점검", "P1"
    if status == "보유" and threat in {"low", "none"}:
        return "유지", "P3"
    if threat == "high":
        return "근거 재확인 후 대응 검토", "P1"
    return "모니터링 유지", "P2"


def _source_link(item: dict[str, Any]) -> str:
    url = item.get("source_url") or item.get("source") or ""
    name = item.get("source_name") or item.get("title") or item.get("source_type") or "출처"
    if str(url).startswith("https://"):
        return f'<a href="{_esc(url)}" target="_blank" rel="noopener">{_esc(name)}</a>'
    return _esc(name)


def _markdown_section(draft: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in draft:
        return ""
    rest = draft.split(marker, 1)[1]
    end = rest.find("\n## ")
    return (rest if end == -1 else rest[:end]).strip()


def _plain_list_html(lines: list[str]) -> str:
    if not lines:
        return '<p class="muted">이번 달 확인된 고신뢰 근거 없음</p>'
    return "<ul>" + "".join(f"<li>{_esc(line)}</li>" for line in lines) + "</ul>"


def _trend_tags(evidence: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in evidence:
        for tag in item.get("dynamic_tags", []) or []:
            if tag not in {item.get("compressor_type"), item.get("category"), item.get("source_type")}:
                counter[str(tag)] += 1
    return counter


def _generate_samsung_insights(state: dict[str, Any]) -> dict[str, list[str]]:
    rows = _flatten_gap_rows(state)
    evidence = _evidence(state)
    immediate: list[str] = []
    monitoring: list[str] = []
    opportunities: list[str] = []
    for row in rows:
        status = row.get("samsung_status", "확인필요")
        level = row.get("threat_level", "none")
        label = f"{row.get('compressor_type')}/{row.get('refrigerant')}/{row.get('condition')} — {row.get('competitor_names') or '경쟁사 확인 필요'}"
        if level == "high" or status == "미보유":
            action, _ = _recommended_action(status, level)
            immediate.append(f"{label}: 삼성 {_status_label(status)}, 권장 액션 '{action}'")
        elif level == "medium":
            monitoring.append(f"{label}: medium threat 지속 모니터링")
        elif status == "보유" or not row.get("competitors"):
            opportunities.append(f"{label}: 삼성 선점/유지 가능 영역")
    if not monitoring:
        medium_items = [e for e in evidence if e.get("threat_level") == "medium"][:3]
        monitoring = [f"{e.get('competitor')} {e.get('compressor_type')} {_safe_join_refs(e)} 신규 냉매/인증 동향 추적" for e in medium_items]
    if not opportunities:
        opportunities = ["경쟁사 근거가 부족한 Gap Matrix cell은 삼성 선점 가능성 후보로 별도 확인 필요"]
    return {"immediate": immediate[:6], "monitoring": monitoring[:6], "opportunities": opportunities[:6]}


def _category_insight_text(category: str, items: list[dict[str, Any]]) -> list[str]:
    competitors = sorted({str(i.get("competitor")) for i in items if i.get("competitor")})
    refs = sorted({ref for i in items for ref in (_safe_join_refs(i).split("/") if _safe_join_refs(i) else []) if ref})
    high = [i for i in items if i.get("threat_level") == "high"]
    primary = [i for i in items if i.get("competitor") in _primary_competitors()]
    if not items:
        return ["이번 달 확인된 고신뢰 근거 없음 — 다음 수집 주기에서 공식 출처 우선 재확인"]
    prefix = f"{len(items)}건 evidence, 관련 경쟁사 {len(competitors)}개({', '.join(competitors[:4])})"
    mapping = {
        "신냉매·냉매전환": [prefix, f"경쟁사 채택 냉매: {', '.join(refs[:6]) or '확인 필요'}", "권장: 삼성이 우선 검토해야 할 냉매 전환 경로를 R290/R454B 중심으로 재점검"],
        "성능·효율": [prefix, "인버터/Variable/COP/EER 키워드 근거를 기준으로 효율 격차 후보를 선별", "권장: 효율 격차 우선 개선 대상 모델을 공식 스펙으로 재확인"],
        "신제품·라인업": [prefix, f"신규/라인업 근거 중 high threat {len(high)}건", "권장: 삼성 Gap 구간을 직접 공략한 신규 라인업 우선 검토"],
        "신뢰성·내구성": [prefix, "경쟁사 신뢰성 인증/필드 이슈 근거를 분리해 추적", "권장: 삼성 미취득 인증 중 경쟁사 보유 항목 우선 확인"],
        "특허·기술": [prefix, "특허/기술 키워드는 인버터·냉매·압축 구조 중심으로 방어/공격 후보화", "권장: 삼성 기술 방향과 충돌 가능한 특허를 별도 리뷰"],
        "규격·인증": [prefix, "US/EU/CN/KR/JP 규격 대응 근거를 source_type=official 중심으로 평가", "권장: 삼성 우선 취득 필요 지역 인증을 도출"],
        "가격·유통": [prefix, "가격·유통 근거는 저신뢰 가능성이 높으므로 참고만 표시", "권장: 가격 경쟁력 우선 점검 구간을 공식/OEM 근거로 재확인"],
        "전시회·발표": [prefix, "전시회 발표는 업계 방향성 시그널로 분리하고 공식 발표와 교차검증", "권장: 삼성이 주목해야 할 다음 전시회와 발표 주제를 지정"],
    }
    lines = mapping.get(category, [prefix])
    if primary:
        lines.append(f"★ 최우선 경쟁사 근거 {len(primary)}건 포함")
    return lines


def _css() -> str:
    return f"""
<style>
:root{{--airbnb-red:{AIRBNB_RED};--medium:{MEDIUM};--safe:{SAFE};--line:{LINE};--card-bg:{CARD_BG};--samsung-blue:{SAMSUNG_BLUE};--category-purple:{CATEGORY_PURPLE};--text:{TEXT};}}
*{{box-sizing:border-box}} body{{margin:0;background:#FFFFFF;color:var(--text);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.55;}}
a{{color:var(--samsung-blue);text-decoration:none}} a:hover{{text-decoration:underline}}
.container{{max-width:1200px;margin:0 auto;padding:32px 24px 64px;}}
.hero{{background:var(--airbnb-red);color:#fff;padding:44px 0;border-radius:0 0 28px 28px;box-shadow:0 2px 8px rgba(0,0,0,0.08);}}
.hero h1{{margin:0 0 12px;font-size:38px;letter-spacing:-0.035em;line-height:1.15}} .hero-meta{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.pill{{display:inline-block;border-radius:999px;background:rgba(255,255,255,.18);padding:7px 13px;font-weight:800}}
.layer-nav,.tabs{{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0}} .tab,.layer-button{{border:1px solid var(--line);background:#fff;border-radius:999px;padding:9px 15px;font-weight:800;color:#222;cursor:pointer}}
.layer-button.active,.tab.active{{background:#222;color:#fff;border-color:#222}}
.layer{{display:none}} .layer.active{{display:block}}
.card{{border:1px solid var(--line);border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);padding:24px;margin:0 0 32px;background:#fff;}}
.card.soft{{background:var(--card-bg)}} .card.samsung-insight{{background:#EBF4FF;border-color:#B9D7FF}} .card.category-insight{{background:#F3EEFF;border-color:#D9C8FF}}
h2{{font-size:26px;margin:0 0 18px;letter-spacing:-0.02em}} h3{{font-size:20px;margin:0 0 14px}} h4{{margin:14px 0 8px}} .muted{{color:#717171}}
.kpi-grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;margin:24px 0 32px}} .kpi-card{{background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);padding:18px}}
.kpi-card strong{{display:block;font-size:30px;letter-spacing:-.03em}} .kpi-card.high strong{{color:var(--airbnb-red)}} .delta{{font-size:12px;font-weight:800;color:#717171}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} .grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.badge{{display:inline-block;border-radius:999px;padding:3px 9px;font-size:12px;font-weight:800;vertical-align:middle;white-space:nowrap}}
table{{width:100%;border-collapse:separate;border-spacing:0;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:#fff}} th{{background:#F7F7F7;text-align:left;padding:12px;border-bottom:1px solid var(--line);font-size:13px}}td{{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}}tr:last-child td{{border-bottom:0}} tr.primary-row td{{background:#FFF8F8;border-left:4px solid var(--airbnb-red)}}
.decision-matrix tr.threat-high td{{background:#FFF0F0}} .decision-matrix tr.threat-medium td{{background:#FFFBF0}}
.heatmap{{display:grid;gap:8px}} .heatmap-row{{display:grid;grid-template-columns:140px repeat(auto-fit,minmax(128px,1fr));gap:8px;align-items:stretch}} .heatmap-head,.heatmap-label{{font-weight:900;padding:10px;background:#F7F7F7;border-radius:10px}}
.heatmap-cell{{border-radius:10px;padding:10px;min-height:72px;border:1px solid var(--line);position:relative}} .heatmap-cell.threat-high{{background:#FFF0F0;border-color:var(--airbnb-red)}} .heatmap-cell.threat-medium{{background:#FFFBF0;border-color:var(--medium)}} .heatmap-cell.threat-low{{background:#F0FFFC;border-color:var(--safe)}} .heatmap-cell.threat-none{{background:#F7F7F7}} .heatmap-cell.data-insufficient{{border-style:dashed;filter:grayscale(.2)}}
.tooltip{{font-size:12px;color:#717171;margin-top:5px}}
.svg-card{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;overflow:auto}}
.category-tabs,.type-tabs{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}} .tab-panel{{display:none}} .tab-panel.active{{display:block}}
.source-card,.competitor-card{{border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0;background:#fff}} .competitor-card.primary{{border-left:4px solid var(--airbnb-red);background:#FFF8F8}}
details{{border-top:1px solid var(--line);padding:14px 0}} summary{{font-weight:900;cursor:pointer}}
.footer-sources{{background:#F7F7F7}} .source-group{{margin:18px 0}} .source-used{{outline:2px solid var(--samsung-blue)}}
.trend-list li{{margin-bottom:8px}} .insight-columns{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}
@media(max-width:980px){{.kpi-grid{{grid-template-columns:repeat(2,1fr)}}.grid-2,.grid-3,.insight-columns{{grid-template-columns:1fr}}.heatmap-row{{grid-template-columns:1fr}}.hero h1{{font-size:30px}}}}
</style>
"""


def _js() -> str:
    return """
<script>
(function(){
  function activate(group, target){
    document.querySelectorAll('[data-group="'+group+'"]').forEach(function(el){el.classList.remove('active');});
    document.querySelectorAll('[data-target-group="'+group+'"]').forEach(function(el){el.classList.remove('active');});
    var panel=document.getElementById(target); if(panel){panel.classList.add('active');}
    var btn=document.querySelector('[data-group="'+group+'"][data-target="'+target+'"]'); if(btn){btn.classList.add('active');}
  }
  document.addEventListener('click', function(e){
    var btn=e.target.closest('[data-target]'); if(!btn) return;
    activate(btn.getAttribute('data-group'), btn.getAttribute('data-target'));
  });
})();
</script>
"""


def build_executive_dashboard(state: dict[str, Any]) -> str:
    meta = _meta(state)
    rows = _flatten_gap_rows(state)
    high_count = sum(1 for r in rows if r.get("threat_level") == "high") or meta.get("high_threat_count", 0)
    gap_missing = sum(1 for r in rows if r.get("samsung_status") == "미보유")
    new_entries = len(_bundle(state).get("new_signals", []))
    score = state.get("score", meta.get("critic_score", 0))
    auto = state.get("auto_approve_result", {}).get("audit_log", {}).get("approve", state.get("auto_approve", False))
    guardian = (state.get("guardian_result") or {}).get("severity", "pass")
    insights = _generate_samsung_insights(state)
    kpis = [
        ("전체 Evidence 수", meta.get("total_evidence_count", 0), "↔", ""),
        ("High Threat 수", high_count, "↑" if high_count else "↔", "high"),
        ("Signal 수", meta.get("signal_count", new_entries), "↑" if new_entries else "↔", ""),
        ("Critic Score", score, "↔", ""),
        ("Gap 미보유 수", gap_missing, "↑" if gap_missing else "↔", "high" if gap_missing else ""),
        ("이번달 신규 진입", new_entries, "↑" if new_entries else "↔", ""),
    ]
    kpi_html = "".join(f'<div class="kpi-card {cls}"><span>{_esc(label)}</span><strong>{_esc(value)}</strong><span class="delta">전월 대비 {delta}</span></div>' for label, value, delta, cls in kpis)
    insight_html = f"""
<section class="card samsung-insight" id="samsung-insight">
  <h2>삼성 관점 핵심 인사이트</h2>
  <div class="insight-columns">
    <div><h3>즉시 대응 필요</h3>{_plain_list_html(insights['immediate'])}</div>
    <div><h3>중기 모니터링</h3>{_plain_list_html(insights['monitoring'])}</div>
    <div><h3>기회 영역</h3>{_plain_list_html(insights['opportunities'])}</div>
  </div>
</section>
"""
    decision_rows = []
    for row in rows[:18]:
        action, priority = _recommended_action(row.get("samsung_status", "확인필요"), row.get("threat_level", "none"))
        q_badge = _badge("데이터 부족", "data_insufficient") if row.get("period_evidence_quality") == "data_insufficient" else ""
        decision_rows.append(
            f'<tr class="{_threat_class(row.get("threat_level"))}"><td>{_esc(row.get("compressor_type"))}</td><td>{_esc(row.get("refrigerant"))}</td><td>{_esc(row.get("condition"))}</td><td>{_badge(row.get("threat_level"), row.get("threat_level"))}</td><td>{_esc(row.get("competitor_names"))} {q_badge}</td><td>{_badge(_status_label(row.get("samsung_status", "확인필요")), row.get("samsung_status"))}</td><td>{_esc(action)}</td><td>{_badge(priority, "high" if priority == "P0" else "medium" if priority == "P1" else "none")}</td></tr>'
        )
    if not decision_rows:
        decision_rows.append('<tr><td colspan="8">이번 달 확인된 Gap Matrix 근거 없음</td></tr>')
    return f"""
<section class="layer active" id="layer-dashboard" data-target-group="main-layer">
  <div class="kpi-grid">{kpi_html}</div>
  {insight_html}
  <section class="card"><h2>Decision Matrix</h2><p class="muted">권장액션 정책: 미보유+high → 즉시 라인업 검토 · 미보유+medium → 6개월 내 대응 계획 · 대응중+medium → 진행 상황 점검 · 보유+low → 유지</p><table class="decision-matrix"><thead><tr><th>타입</th><th>냉매</th><th>조건</th><th>위협도</th><th>경쟁사</th><th>삼성현황</th><th>권장액션</th><th>우선순위</th></tr></thead><tbody>{''.join(decision_rows)}</tbody></table></section>
  {_build_trend_insights(state)}
  {_build_positioning_map(state)}
  {_build_monthly_changes(state)}
</section>
"""


def _build_heatmap(state: dict[str, Any], ctype: str) -> str:
    rows = [r for r in _flatten_gap_rows(state) if r.get("compressor_type") == ctype]
    refs = sorted({str(r.get("refrigerant")) for r in rows if r.get("refrigerant")}) or ["확인필요"]
    conditions = sorted({str(r.get("condition")) for r in rows if r.get("condition")}) or ["default"]
    cell_map = {(str(r.get("refrigerant")), str(r.get("condition"))): r for r in rows}
    header = '<div class="heatmap-row"><div class="heatmap-head">냉매/조건</div>' + ''.join(f'<div class="heatmap-head">{_esc(c)}</div>' for c in conditions) + '</div>'
    body = []
    for ref in refs:
        cells = [f'<div class="heatmap-label">{_esc(ref)}</div>']
        for cond in conditions:
            row = cell_map.get((ref, cond), {"threat_level": "none", "samsung_status": "확인필요", "competitors": [], "competitor_names": ""})
            level = row.get("threat_level", "none")
            qcls = " data-insufficient" if row.get("period_evidence_quality") == "data_insufficient" else ""
            comp_count = len(row.get("competitors") or [])
            cells.append(f'<div class="heatmap-cell {_threat_class(level)}{qcls}" title="{_esc(row.get("competitor_names"))} trust/source 확인"><strong>{_esc(_status_label(row.get("samsung_status", "확인필요")))}</strong><br>{_badge(level, level)}<div class="tooltip">경쟁사 {comp_count}개<br>{_esc(row.get("competitor_names"))}</div></div>')
        body.append('<div class="heatmap-row">' + ''.join(cells) + '</div>')
    return f'<div class="gap-heatmap heatmap">{header}{"".join(body)}</div>'


def _competitor_metrics(evidence: list[dict[str, Any]], competitor: str, ctype: str | None = None) -> dict[str, int]:
    items = [e for e in evidence if e.get("competitor") == competitor and (ctype is None or e.get("compressor_type") == ctype)]
    refs = {ref for e in items for ref in _safe_join_refs(e).split("/") if ref}
    cats = Counter(e.get("category") for e in items)
    patents = sum(1 for e in items if e.get("source_type") == "patent" or e.get("category") == "특허·기술")
    certifications = sum(1 for e in items if e.get("category") == "규격·인증" or "certification" in (e.get("dynamic_tags") or []))
    performance = sum(1 for e in items if e.get("category") == "성능·효율" or any(tag in (e.get("dynamic_tags") or []) for tag in ["performance", "variable", "inverter"]))
    return {"효율": min(5, performance + 1), "신제품": min(5, cats.get("신제품·라인업", 0) + 1), "냉매": min(5, len(refs)), "인증": min(5, certifications + 1), "특허": min(5, patents + 1), "evidence": len(items)}


def _radar_svg(evidence: list[dict[str, Any]], competitors: list[str], ctype: str) -> str:
    axes = ["효율", "신제품", "냉매", "인증", "특허"]
    bars = []
    for idx, comp in enumerate(competitors[:6]):
        metrics = _competitor_metrics(evidence, comp, ctype)
        y = 28 + idx * 30
        bars.append(f'<text x="10" y="{y+14}" font-size="12" font-weight="700">{_esc(comp)}</text>')
        for a_idx, axis in enumerate(axes):
            value = metrics[axis]
            x = 160 + a_idx * 90
            color = AIRBNB_RED if comp in _primary_competitors() else SAFE
            bars.append(f'<rect x="{x}" y="{y}" width="{value*14}" height="16" rx="4" fill="{color}" opacity="0.82"><title>{_esc(axis)} {value}/5</title></rect>')
    axis_labels = ''.join(f'<text x="{160+i*90}" y="18" font-size="11" fill="#717171">{_esc(axis)}</text>' for i, axis in enumerate(axes))
    samsung_line = '<line x1="202" y1="20" x2="202" y2="220" stroke="#222" stroke-dasharray="4 4"/><text x="206" y="214" font-size="11">Samsung baseline 추정</text>'
    return f'<div class="svg-card"><svg class="competitor-chart" width="680" height="230" role="img" aria-label="경쟁사 비교 바 차트">{axis_labels}{samsung_line}{"".join(bars)}</svg></div>'


def _competitor_table(evidence: list[dict[str, Any]], ctype: str) -> str:
    items = sorted([e for e in evidence if e.get("compressor_type") == ctype], key=lambda e: (_competitor_order(str(e.get("competitor"))), THREAT_ORDER.get(e.get("threat_level", "none"), 9), -int(e.get("trust_score", 0))))
    rows = []
    for item in items:
        primary = item.get("competitor") in PRIMARY_COMPETITORS.get(ctype, [])
        rows.append(f'<tr class="{"primary-row" if primary else ""}"><td>{"★ " if primary else ""}{_esc(item.get("competitor"))}</td><td>{_esc(item.get("product_or_series", "확인필요"))}</td><td>{_esc(_safe_join_refs(item))}</td><td>{_badge(_status_label(item.get("samsung_status", "확인필요")), item.get("samsung_status"))}</td><td>{_badge(item.get("threat_level", "none"), item.get("threat_level", "none"))}</td><td>{_esc(item.get("trust_score"))}</td><td>{_source_link(item)}</td><td>{_esc(item.get("source_date"))}</td></tr>')
    if not rows:
        rows.append('<tr><td colspan="8">이번 달 확인된 고신뢰 근거 없음</td></tr>')
    return '<table><thead><tr><th>경쟁사</th><th>주요 모델</th><th>냉매</th><th>삼성 대비</th><th>위협도</th><th>trust_score</th><th>출처</th><th>날짜</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'


def _category_heatmap(evidence: list[dict[str, Any]], ctype: str) -> str:
    competitors = sorted({e.get("competitor") for e in evidence if e.get("compressor_type") == ctype}, key=lambda c: _competitor_order(str(c))) or (PRIMARY_COMPETITORS.get(ctype, []) + SECONDARY_COMPETITORS.get(ctype, []))
    header = '<tr><th>카테고리</th>' + ''.join(f'<th>{_esc(c)}</th>' for c in competitors) + '</tr>'
    rows = []
    for cat in CATEGORIES:
        cells = [f'<td><strong>{_esc(cat)}</strong></td>']
        for comp in competitors:
            items = [e for e in evidence if e.get("compressor_type") == ctype and e.get("category") == cat and e.get("competitor") == comp]
            level = sorted([e.get("threat_level", "none") for e in items], key=lambda l: THREAT_ORDER.get(l, 9))[0] if items else "none"
            cells.append(f'<td class="{_threat_class(level)}">{len(items)} {_badge(level, level)}</td>')
        rows.append('<tr>' + ''.join(cells) + '</tr>')
    return '<table class="category-heatmap"><thead>' + header + '</thead><tbody>' + ''.join(rows) + '</tbody></table>'


def build_comparison_analysis(state: dict[str, Any]) -> str:
    evidence = _evidence(state)
    type_buttons = ''.join(f'<button class="tab {"active" if idx == 0 else ""}" data-group="type-tabs" data-target="type-{ctype}">{ctype}</button>' for idx, ctype in enumerate(("Re", "Ro", "Sc")))
    panels = []
    for idx, ctype in enumerate(("Re", "Ro", "Sc")):
        comps = sorted({e.get("competitor") for e in evidence if e.get("compressor_type") == ctype}, key=lambda c: _competitor_order(str(c))) or PRIMARY_COMPETITORS.get(ctype, [])
        panels.append(f"""
<div class="tab-panel {'active' if idx == 0 else ''}" id="type-{ctype}" data-target-group="type-tabs">
  <section class="card"><h2>{ctype} {TYPE_LABELS.get(ctype, '')} — 삼성 Gap Heatmap</h2>{_build_heatmap(state, ctype)}</section>
  <section class="card"><h2>{ctype} 경쟁사 비교 레이더/바 차트</h2>{_radar_svg(evidence, [str(c) for c in comps], ctype)}</section>
  <section class="card"><h2>{ctype} 경쟁사별 비교 테이블</h2>{_competitor_table(evidence, ctype)}</section>
  <section class="card"><h2>{ctype} 카테고리별 히트맵</h2>{_category_heatmap(evidence, ctype)}</section>
</div>
""")
    matrix_rows = []
    for comp, items in _group_by_competitor(evidence).items():
        by_type = {ctype: [i for i in items if i.get("compressor_type") == ctype] for ctype in ("Re", "Ro", "Sc")}
        cells = []
        for ctype in ("Re", "Ro", "Sc"):
            level = sorted([i.get("threat_level", "none") for i in by_type[ctype]], key=lambda l: THREAT_ORDER.get(l, 9))[0] if by_type[ctype] else "none"
            cells.append(f'<td>{_badge(level, level)}</td>')
        matrix_rows.append(f'<tr class="{"primary-row" if comp in _primary_competitors() else ""}"><td>{"★ " if comp in _primary_competitors() else ""}{_esc(comp)}</td>{"".join(cells)}<td>{len(items)}</td><td>{max([int(i.get("trust_score", 0)) for i in items] or [0])}</td><td>{_badge("신규" if any(i.get("threat_level") in {"high", "medium"} for i in items) else "유지", "medium" if any(i.get("threat_level") in {"high", "medium"} for i in items) else "none")}</td></tr>')
    return f"""
<section class="layer" id="layer-comparison" data-target-group="main-layer">
  <div class="type-tabs">{type_buttons}</div>
  {''.join(panels)}
  <section class="card"><h2>전체 경쟁사 비교 매트릭스</h2><table><thead><tr><th>경쟁사</th><th>Re위협</th><th>Ro위협</th><th>Sc위협</th><th>총 evidence</th><th>최고 trust</th><th>이번달 신규</th></tr></thead><tbody>{''.join(matrix_rows) or '<tr><td colspan="7">근거 없음</td></tr>'}</tbody></table></section>
</section>
"""


def build_category_insights(state: dict[str, Any]) -> str:
    evidence = _evidence(state)
    grouped = _group_by_category(evidence)
    buttons = ''.join(f'<button class="tab {"active" if idx == 0 else ""}" data-group="category-tabs" data-target="cat-{_slug(cat)}">{_esc(cat)}</button>' for idx, cat in enumerate(CATEGORIES))
    panels = []
    for idx, cat in enumerate(CATEGORIES):
        items = grouped.get(cat, [])
        comps = sorted({i.get("competitor") for i in items if i.get("competitor")}, key=lambda c: _competitor_order(str(c)))
        dist = Counter(i.get("threat_level", "none") for i in items)
        active_comp = Counter(i.get("competitor") for i in items).most_common(1)
        kpis = f"""
<div class="kpi-grid">
  <div class="kpi-card"><span>Evidence</span><strong>{len(items)}</strong><span class="delta">카테고리 근거</span></div>
  <div class="kpi-card"><span>경쟁사 수</span><strong>{len(comps)}</strong><span class="delta">관련 경쟁사</span></div>
  <div class="kpi-card high"><span>High</span><strong>{dist.get('high',0)}</strong><span class="delta">위협 분포</span></div>
  <div class="kpi-card"><span>Medium</span><strong>{dist.get('medium',0)}</strong><span class="delta">위협 분포</span></div>
  <div class="kpi-card"><span>Low</span><strong>{dist.get('low',0)}</strong><span class="delta">위협 분포</span></div>
  <div class="kpi-card"><span>가장 활발한 경쟁사</span><strong style="font-size:20px">{_esc(active_comp[0][0] if active_comp else '없음')}</strong><span class="delta">evidence 기준</span></div>
</div>
"""
        insight = '<section class="card category-insight"><h2>' + _esc(cat) + ' — 삼성이 알아야 할 것</h2>' + _plain_list_html(_category_insight_text(cat, items)) + '</section>'
        rows = []
        for comp in comps:
            comp_items = [i for i in items if i.get("competitor") == comp]
            top = sorted(comp_items, key=lambda i: THREAT_ORDER.get(i.get("threat_level", "none"), 9))[0]
            rows.append(f'<tr class="{"primary-row" if comp in _primary_competitors() else ""}"><td>{"★ " if comp in _primary_competitors() else ""}{_esc(comp)}</td><td>{_esc(top.get("raw_text") or top.get("summary"))}</td><td>{_badge(_status_label(top.get("samsung_status", "확인필요")), top.get("samsung_status"))}</td><td>{_badge(top.get("threat_level", "none"), top.get("threat_level", "none"))}</td><td>{_source_link(top)}</td></tr>')
        if not rows:
            rows.append('<tr><td colspan="5">이번 달 확인된 고신뢰 근거 없음</td></tr>')
        source_cards = []
        for item in items:
            low = int(item.get("trust_score", 0)) < 4
            source_cards.append(f'<div class="source-card"><strong>{_source_link(item)}</strong> {_badge(item.get("source_type", "source"), item.get("source_type"))} {_badge("trust=" + str(item.get("trust_score")), "medium" if low else "low")} { _badge("저신뢰 — 단정 금지", "medium") if low else ""}<br><span class="muted">URL: {_esc(item.get("source_url"))} · 날짜: {_esc(item.get("source_date"))}</span></div>')
        source_html = ''.join(source_cards) or '<p class="muted">이번 달 확인된 고신뢰 근거 없음</p>'
        panels.append(f"""
<div class="tab-panel {'active' if idx == 0 else ''}" id="cat-{_slug(cat)}" data-target-group="category-tabs">
  <section class="card"><h2>{_esc(cat)} KPI 요약</h2>{kpis}</section>
  {insight}
  <section class="card"><h2>{_esc(cat)} 경쟁사 비교 테이블</h2><table><thead><tr><th>경쟁사</th><th>주요 내용</th><th>삼성 비교</th><th>위협도</th><th>출처</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>
  <section class="card"><h2>{_esc(cat)} 출처 목록</h2>{source_html}</section>
</div>
""")
    return f"""
<section class="layer" id="layer-category" data-target-group="main-layer">
  <section class="card"><h2>카테고리별 삼성 인사이트 분석</h2><div class="category-tabs">{buttons}</div>{''.join(panels)}</section>
</section>
"""


def _competitor_profile(comp: str, items: list[dict[str, Any]]) -> str:
    types = sorted({i.get("compressor_type") for i in items})
    high = sum(1 for i in items if i.get("threat_level") == "high")
    strength = "높음" if comp in _primary_competitors() or high else "보통"
    return f'<div class="competitor-card {"primary" if comp in _primary_competitors() else ""}"><h3>{"★ " if comp in _primary_competitors() else ""}{_esc(comp)}</h3><p>주력 타입: {" ".join(_badge(t, "none") for t in types) or "확인 필요"}</p><p>삼성과의 경쟁 강도: <strong>{_esc(strength)}</strong></p><p>이번 달 주요 변화: evidence {len(items)}건, high threat {high}건</p></div>'


def build_competitor_deepdive(state: dict[str, Any]) -> str:
    grouped = _group_by_competitor(_evidence(state))
    sections = []
    for comp, items in grouped.items():
        open_attr = " open" if comp in _primary_competitors() else ""
        lineup_rows = []
        for item in sorted(items, key=lambda i: (i.get("compressor_type", ""), THREAT_ORDER.get(i.get("threat_level", "none"), 9))):
            lineup_rows.append(f'<tr><td>{_esc(item.get("product_or_series", "확인필요"))}</td><td>{_esc(item.get("compressor_type"))}</td><td>{_esc(_safe_join_refs(item))}</td><td>{_esc(item.get("condition_or_capacity", "확인필요"))}</td><td>{_badge(_status_label(item.get("samsung_status", "확인필요")), item.get("samsung_status"))}</td><td>{_esc(item.get("trust_score"))}</td></tr>')
        cat_details = []
        for cat in CATEGORIES:
            cat_items = [i for i in items if i.get("category") == cat]
            body = ''.join(f'<li>{_esc(i.get("raw_text") or i.get("summary"))} {_badge(i.get("threat_level", "none"), i.get("threat_level", "none"))} {_source_link(i)}</li>' for i in cat_items) or '<li class="muted">이번 달 확인된 고신뢰 근거 없음</li>'
            cat_details.append(f'<details><summary>{_esc(cat)}</summary><ul>{body}</ul></details>')
        ahead = [i for i in items if i.get("samsung_status") in {"미보유", "대응중"}]
        source_cards = ''.join(f'<div class="source-card">{_source_link(i)} {_badge(i.get("source_type", "source"), i.get("source_type"))} {_badge("trust=" + str(i.get("trust_score")), "medium" if int(i.get("trust_score",0)) < 4 else "low")}<br><span class="muted">{_esc(i.get("source_url"))} · {_esc(i.get("source_date"))}</span></div>' for i in items) or '<p class="muted">이번 달 확인된 고신뢰 근거 없음</p>'
        sections.append(f"""
<details class="competitor-deepdive"{open_attr}><summary>{'★ ' if comp in _primary_competitors() else ''}{_esc(comp)} 심화 보고서</summary>
  {_competitor_profile(comp, items)}
  <section class="card"><h3>제품 라인업 분석</h3><table><thead><tr><th>모델명</th><th>타입</th><th>냉매</th><th>조건</th><th>삼성 대비</th><th>trust_score</th></tr></thead><tbody>{''.join(lineup_rows) or '<tr><td colspan="6">이번 달 확인된 고신뢰 근거 없음</td></tr>'}</tbody></table></section>
  <section class="card"><h3>카테고리별 상세 분석</h3>{''.join(cat_details)}</section>
  <section class="card samsung-insight"><h3>삼성 대비 인사이트</h3>{_plain_list_html([f'{comp}가 삼성보다 앞선 후보 영역: {len(ahead)}건', '삼성 우위 영역은 보유/low threat cell 중심으로 유지 전략 검토', f'{comp} 대응 권장 액션: high/medium threat 근거 우선 재검증'])}</section>
  <section class="card"><h3>출처 및 근거 목록</h3>{source_cards}</section>
</details>
""")
    if not sections:
        sections.append('<p class="muted">이번 달 확인된 경쟁사 근거 없음</p>')
    return f'<section class="layer" id="layer-deepdive" data-target-group="main-layer"><section class="card"><h2>경쟁사별 심화 보고서</h2>{"".join(sections)}</section></section>'


def build_source_reference(state: dict[str, Any]) -> str:
    used_urls = {str(s.get("source_url")) for s in state.get("sources", [])} | {str(e.get("source_url")) for e in _evidence(state)}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in flatten_source_whitelist():
        groups[source.get("group", "기타")].append(source)
    preferred_order = ["competitors_official", "regulations", "standards", "patents", "exhibitions", "natural_refrigerants", "trade_media", "industry_media", "academic_title_abstract_only"]
    labels = {
        "competitors_official": "경쟁사 공식 (trust=5)",
        "regulations": "규제 기관 (trust=5)",
        "standards": "규제/표준 (trust=5)",
        "patents": "특허 DB (trust=5)",
        "exhibitions": "전시회 (trust=5)",
        "natural_refrigerants": "자연냉매 보완 (trust=4)",
        "trade_media": "업계 미디어 (trust=3~4)",
        "industry_media": "업계 미디어 (trust=3~4)",
        "academic_title_abstract_only": "학술 (trust=4)",
    }
    html_groups = []
    for group in preferred_order:
        if group not in groups:
            continue
        cards = []
        for s in groups[group]:
            used = s.get("url") in used_urls or any(str(u).startswith(str(s.get("url"))) for u in used_urls)
            cards.append(f'<li class="{"source-used" if used else ""}"><a href="{_esc(s.get("url"))}" target="_blank" rel="noopener">{_esc(s.get("name"))}</a> {_badge("trust=" + str(s.get("trust_score")), "low" if int(s.get("trust_score",0)) >= 4 else "medium")} {_badge("이번 달 활용" if used else "미활용", "low" if used else "none")}</li>')
        html_groups.append(f'<div class="source-group"><h3>{_esc(labels.get(group, group))}</h3><ul>{"".join(cards)}</ul></div>')
    return f'<section class="card footer-sources"><h2>모니터링 소스 전체 목록</h2>{"".join(html_groups)}</section>'


def _build_trend_insights(state: dict[str, Any]) -> str:
    evidence = _evidence(state)
    signals = _bundle(state).get("new_signals", [])
    tags = _trend_tags(evidence)
    lines = []
    if any("R290" in _safe_join_refs(e) or "R454B" in _safe_join_refs(e) for e in evidence):
        lines.append("냉매 전환 시그널: R290/R454B 중심 근거가 감지되어 냉매 전환 가속 여부 추적 필요")
    if any(tag in tags for tag in ["variable", "inverter", "performance"]):
        lines.append("기술 시그널: Variable/인버터/효율 관련 근거가 존재해 성능 경쟁 축 확대 가능")
    if signals:
        lines.append(f"신규/이상 신호 {len(signals)}건 감지 — high/medium threat와 교차 검증 필요")
    if not lines:
        lines.append("이번 달 업계 전체 방향은 데이터 부족으로 단정 불가")
    return '<section class="card"><h2>트렌드 인사이트</h2><ul class="trend-list">' + ''.join(f'<li>{_esc(line)}</li>' for line in lines) + '</ul></section>'


def _build_positioning_map(state: dict[str, Any]) -> str:
    evidence = _evidence(state)
    grouped = _group_by_competitor(evidence)
    bubbles = []
    for idx, (comp, items) in enumerate(grouped.items()):
        refs = {ref for i in items for ref in _safe_join_refs(i).split("/") if ref}
        perf = sum(1 for i in items if i.get("category") == "성능·효율" or "performance" in (i.get("dynamic_tags") or []))
        x = 80 + min(320, len(refs) * 55 + int(max([i.get("trust_score", 0) for i in items] or [0])) * 18)
        y = 260 - min(190, perf * 35 + len(items) * 8)
        r = 10 + min(24, len(items) * 3)
        color = AIRBNB_RED if comp in _primary_competitors() else SAFE
        bubbles.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="0.78"><title>{_esc(comp)} evidence={len(items)}</title></circle><text x="{x+12}" y="{y}" font-size="12">{_esc(comp)}</text>')
    samsung = '<polygon points="85,180 91,197 110,197 95,208 101,226 85,215 69,226 75,208 60,197 79,197" fill="#222"><title>Samsung 기준 위치(추정)</title></polygon><text x="110" y="188" font-size="12" font-weight="700">Samsung 추정</text>'
    return f'<section class="card"><h2>삼성 포지셔닝 맵 <span class="muted">(trust/evidence 기반 추정)</span></h2><div class="svg-card"><svg width="620" height="310" role="img" aria-label="삼성 포지셔닝 맵"><line x1="60" y1="270" x2="560" y2="270" stroke="#999"/><line x1="60" y1="270" x2="60" y2="40" stroke="#999"/><text x="230" y="300" font-size="12">냉매 전환 준비도</text><text x="8" y="44" font-size="12">효율 경쟁력</text>{samsung}{"".join(bubbles)}</svg></div></section>'


def _build_monthly_changes(state: dict[str, Any]) -> str:
    changes = state.get("state_changes") or state.get("monthly_changes") or []
    if not changes:
        body = '<p class="muted">이전 기간 데이터 부족으로 비교 불가 또는 상태 변화 없음</p>'
    else:
        body = '<ul>' + ''.join(f'<li>{_esc(c)}</li>' for c in changes[:10]) + '</ul>'
    return f'<section class="card"><h2>월간 변화 요약</h2>{body}</section>'


def build_full_report(state: dict[str, Any]) -> str:
    draft = state.get("draft", "")
    title = draft.splitlines()[0].replace("#", "").strip() if draft else "압축기 경쟁사 월간 모니터링 리포트"
    period = _period_id(state)
    auto = state.get("auto_approve_result", {}).get("audit_log", {}).get("approve", state.get("auto_approve", False))
    guardian = (state.get("guardian_result") or {}).get("severity", "pass")
    generated_at = datetime.now().isoformat(timespec="seconds")
    quality = "data_insufficient" if any(e.get("period_evidence_quality") == "data_insufficient" for e in _evidence(state)) else "sufficient"
    nav = "".join([
        '<button class="layer-button active" data-group="main-layer" data-target="layer-dashboard">Layer 1 Executive Dashboard</button>',
        '<button class="layer-button" data-group="main-layer" data-target="layer-comparison">Layer 2 비교 분석</button>',
        '<button class="layer-button" data-group="main-layer" data-target="layer-category">Layer 3 카테고리 인사이트</button>',
        '<button class="layer-button" data-group="main-layer" data-target="layer-deepdive">Layer 4 심화 보고서</button>',
    ])
    return f"""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{_css()}<title>{_esc(title)}</title></head>
<body>
  <header class="hero"><div class="container"><h1>{_esc(title)}</h1><div class="hero-meta"><span class="pill">기간 { _esc(period) }</span><span class="pill">생성 { _esc(generated_at) }</span><span class="pill">Auto-approve { _esc('승인' if auto else '미승인/미평가') }</span><span class="pill">Guardian { _esc(guardian) }</span><span class="pill">Data { _esc(quality) }</span></div></div></header>
  <main class="container"><nav class="layer-nav">{nav}</nav>{build_executive_dashboard(state)}{build_comparison_analysis(state)}{build_category_insights(state)}{build_competitor_deepdive(state)}{build_source_reference(state)}</main>{_js()}
</body></html>
"""


def markdown_to_html(draft: str, state: dict[str, Any]) -> str:
    return build_full_report({**state, "draft": draft})


def build_backfill_html(summary: dict[str, Any]) -> str:
    snapshots = summary.get("period_snapshots", [])
    latest = summary.get("latest", {})
    rows = []
    for snap in snapshots:
        quality = snap.get("evidence_quality", "unknown")
        rows.append(f'<tr><td>{_esc(snap.get("period_id"))}</td><td>{_esc(snap.get("evidence_count"))}</td><td>{_badge(quality, "data_insufficient" if quality == "data_insufficient" else "low")}</td><td>{_esc(snap.get("signal_count"))}</td><td>{_esc(snap.get("threat_count"))}</td><td>{_esc(", ".join(snap.get("source_boosts", [])))}</td></tr>')
    changes = summary.get("state_changes", [])
    changes_html = '<ul>' + ''.join(f'<li>{_esc(c.get("from_period"))}→{_esc(c.get("to_period"))} {_esc(c.get("compressor_type"))}/{_esc(c.get("refrigerant"))}/{_esc(c.get("condition"))}: {_esc(c.get("from_status"))}→{_esc(c.get("to_status"))}</li>' for c in changes) + '</ul>' if changes else '<p class="muted">상태 변화 없음 또는 dry-run stub 기준 동일</p>'
    pseudo_state = {"period_id": latest.get("period_id"), "analysis_bundle": {"gap_matrix": latest.get("gap_matrix", {})}, "evidence": [], "sources": [], "score": "backfill"}
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{_css()}<title>Backfill Gap Summary</title></head><body><header class="hero"><div class="container"><h1>Backfill Gap Summary</h1><div class="hero-meta"><span class="pill">{_esc(summary.get('from_period'))} ~ {_esc(summary.get('to_period'))}</span><span class="pill">dry_run={_esc(summary.get('dry_run'))}</span><span class="pill">latest={_esc(latest.get('period_id'))}</span></div></div></header><main class="container"><section class="card"><h2>Period Timeline</h2><table><thead><tr><th>period</th><th>evidence</th><th>quality</th><th>signals</th><th>threats</th><th>boost sources</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section><section class="card"><h2>Latest Gap Matrix</h2>{_build_heatmap(pseudo_state, 'Re')}{_build_heatmap(pseudo_state, 'Ro')}{_build_heatmap(pseudo_state, 'Sc')}</section><section class="card"><h2>Period간 상태 변화 이력</h2>{changes_html}</section>{build_source_reference(pseudo_state)}</main></body></html>"""
