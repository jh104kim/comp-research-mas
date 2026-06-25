from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ResearchAdapter:
    """Interface for Hermes/out-of-repo research execution."""

    def search(self, query_plan: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class StubResearchAdapter(ResearchAdapter):
    """Deterministic STEP 2 stub. No network, no crawling."""

    def search(self, query_plan: dict[str, Any]) -> dict[str, Any]:
        results = []
        primary = [q for q in query_plan["queries"] if str(q["priority"]).startswith("primary")]
        selected = []
        offsets = {"Re": 0, "Ro": 2, "Sc": 0}
        for ctype in ("Re", "Ro", "Sc"):
            ctype_queries = [q for q in primary if q["compressor_type"] == ctype]
            offset = offsets[ctype]
            selected.extend(ctype_queries[offset : offset + 2])
        for q in selected:
            results.append(_result_from_query(q))
        if results:
            duplicate = dict(results[0])
            duplicate["source_type"] = "news"
            duplicate["source_url"] = duplicate["source_url"] + "?dup=news"
            results.append(duplicate)
        return {"week_id": query_plan["week_id"], "period_id": query_plan.get("period_id", query_plan["week_id"]), "results": results}


class Step3StubResearchAdapter(ResearchAdapter):
    """Deterministic STEP 3 stub with anomaly-trigger data. No network."""

    def search(self, query_plan: dict[str, Any]) -> dict[str, Any]:
        base_results = StubResearchAdapter().search(query_plan)["results"]
        week_id = query_plan["week_id"]
        anomaly_results = [
            {
                "query_id": "Sc_Copeland_Emerson_R454B_Variable_signal",
                "week_id": week_id,
                "compressor_type": "Sc",
                "competitor": "Copeland/Emerson",
                "category": "신제품·라인업",
                "refrigerants": ["R454B"],
                "source_url": "https://example.com/step3/copeland-r454b-variable",
                "source_date": "2026-06-20",
                "source_type": "official",
                "title": "Copeland R454B Variable Scroll 신규 진입",
                "summary": "Copeland/Emerson R454B Variable Scroll 신규 진입. 삼성 미보유 구간.",
                "raw_text": "Copeland/Emerson Sc R454B Variable Scroll. 삼성 상태: 미보유. ★ 최우선 경쟁사 신규 진입.",
                "samsung_status": "미보유",
            },
            {
                "query_id": "Re_LG_R290_MBP_signal",
                "week_id": week_id,
                "compressor_type": "Re",
                "competitor": "LG",
                "category": "신냉매·냉매전환",
                "refrigerants": ["R290"],
                "source_url": "https://example.com/step3/lg-r290-mbp",
                "source_date": "2026-06-20",
                "source_type": "exhibition",
                "title": "LG R290 MBP Re 신규 채택",
                "summary": "LG R290 MBP Reciprocating 라인업 신호. 삼성 미보유 구간.",
                "raw_text": "LG Re R290 MBP. 삼성 상태: 미보유. GMCC와 동일 구간 동시 진입 시나리오.",
                "samsung_status": "미보유",
            },
            {
                "query_id": "Re_GMCC_Midea_R290_MBP_signal",
                "week_id": week_id,
                "compressor_type": "Re",
                "competitor": "GMCC/Midea",
                "category": "신냉매·냉매전환",
                "refrigerants": ["R290"],
                "source_url": "https://example.com/step3/gmcc-r290-mbp",
                "source_date": "2026-06-20",
                "source_type": "official",
                "title": "GMCC R290 MBP Re 재등장",
                "summary": "GMCC/Midea R290 MBP Reciprocating 2주 내 재등장.",
                "raw_text": "GMCC/Midea Re R290 MBP. 삼성 상태: 미보유. 동일 모델 2주 내 재등장.",
                "samsung_status": "미보유",
            },
        ]
        return {"week_id": week_id, "period_id": query_plan.get("period_id", week_id), "results": base_results + anomaly_results}


def _result_from_query(q: dict[str, Any]) -> dict[str, Any]:
    competitor = q["competitor"]
    ctype = q["compressor_type"]
    category = q["category"]
    source_type = "trade_media"
    samsung_status = "확인필요"
    threat_phrase = "삼성 현황 확인 필요"
    if competitor == "GMCC/Midea" and ctype == "Re":
        samsung_status = "미보유"
        threat_phrase = "삼성 미보유 구간 진입 신호"
        source_type = "official"
    elif competitor == "Copeland/Emerson" and ctype == "Sc":
        samsung_status = "대응중"
        threat_phrase = "삼성 대응 중 구간의 북미 경쟁 심화"
        source_type = "trade_media"
    elif competitor == "LG" and ctype == "Ro":
        samsung_status = "확인필요"
        threat_phrase = "CE 인증 기반 확인 필요"
        source_type = "exhibition"
    return {
        "query_id": q["query_id"],
        "week_id": q["week_id"],
        "compressor_type": ctype,
        "competitor": competitor,
        "category": category,
        "refrigerants": q["refrigerants"][:2],
        "source_url": f"https://example.com/{q['query_id']}",
        "source_date": "2026-06-20",
        "source_type": source_type,
        "title": f"{competitor} {ctype} {category} update",
        "summary": f"{competitor} {ctype} {category} 관련 선별 stub 결과. {threat_phrase}.",
        "raw_text": f"{competitor} {ctype} {category}. 삼성 상태: {samsung_status}. {threat_phrase}.",
        "samsung_status": samsung_status,
    }


def save_raw_results(raw_results: dict[str, Any], output_dir: str | Path = "outputs/search") -> Path:
    path = Path(output_dir) / f"{raw_results['week_id']}_raw_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw_results, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
