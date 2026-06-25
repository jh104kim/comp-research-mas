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
        primary = [q for q in query_plan["queries"] if q["priority"] == "primary"]
        selected = []
        offsets = {"Re": 0, "Ro": 2, "Sc": 0}
        for ctype in ("Re", "Ro", "Sc"):
            ctype_queries = [q for q in primary if q["compressor_type"] == ctype]
            offset = offsets[ctype]
            selected.extend(ctype_queries[offset : offset + 2])
        for q in selected:
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
            results.append(
                {
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
            )
        # Duplicate with lower trust to verify dedup keeps stronger result.
        if results:
            duplicate = dict(results[0])
            duplicate["source_type"] = "news"
            duplicate["source_url"] = duplicate["source_url"] + "?dup=news"
            results.append(duplicate)
        return {"week_id": query_plan["week_id"], "results": results}


def save_raw_results(raw_results: dict[str, Any], output_dir: str | Path = "outputs/search") -> Path:
    path = Path(output_dir) / f"{raw_results['week_id']}_raw_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw_results, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
