from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import (
    CATEGORY_ALIASES,
    COMPETITOR_ALIASES,
    PRIMARY_COMPETITORS,
    SOURCE_TRUST_SCORE,
    EvidenceItem,
)


def normalize_competitor(name: str) -> str:
    clean = name.strip()
    return COMPETITOR_ALIASES.get(clean, clean)


def normalize_category(category: str) -> str:
    return CATEGORY_ALIASES.get(category.strip(), category.strip())


def normalize_samsung_status(value: str | None, text: str = "") -> str:
    combined = f"{value or ''} {text}"
    if "미보유" in combined or "미대응" in combined or "부재" in combined:
        return "미보유"
    if "대응중" in combined or "대응 중" in combined:
        return "대응중"
    if "확인필요" in combined or "확인 필요" in combined:
        return "확인필요"
    if "보유" in combined:
        return "보유"
    return "확인필요"


def extract_refrigerants(value: Any, text: str = "") -> list[str]:
    refs: list[str] = []
    if isinstance(value, list):
        refs.extend(str(v) for v in value)
    elif isinstance(value, str):
        refs.extend(re.split(r"[/,\s]+", value))
    refs.extend(re.findall(r"R\d{2,4}[A-Za-z]?", text))
    unique = []
    for ref in refs:
        clean = ref.strip()
        if clean and clean.startswith("R") and clean not in unique:
            unique.append(clean)
    return unique or ["확인필요"]


def trust_score(source_type: str) -> int:
    return SOURCE_TRUST_SCORE.get(source_type, 1)


def threat_level(samsung_status: str, score: int) -> str:
    if samsung_status == "미보유" and score == 5:
        return "high"
    if samsung_status == "미보유" and score in {3, 4}:
        return "medium"
    if samsung_status == "대응중" and score >= 4:
        return "medium"
    if samsung_status == "대응중" and score == 3:
        return "low"
    if samsung_status == "보유":
        return "low"
    return "none"


def dynamic_tags(raw: dict[str, Any], item: EvidenceItem) -> list[str]:
    tags = [item.compressor_type, item.category, item.source_type]
    text = " ".join(str(raw.get(k, "")) for k in ["title", "summary", "raw_text"])
    for ref in item.refrigerant:
        if ref != "확인필요":
            tags.append(ref)
    for token, tag in {
        "인버터": "inverter",
        "Variable": "variable",
        "Two-Stage": "two-stage",
        "CE": "certification",
        "UL": "certification",
        "EER": "performance",
        "COP": "performance",
        "로드맵": "roadmap",
    }.items():
        if token in text and tag not in tags:
            tags.append(tag)
    return tags


def normalize_raw_results(raw_results: dict[str, Any]) -> list[EvidenceItem]:
    week_id = raw_results["week_id"]
    candidates: list[EvidenceItem] = []
    for raw in raw_results.get("results", []):
        competitor = normalize_competitor(raw.get("competitor", "확인필요"))
        ctype = raw.get("compressor_type", "Re")
        source_type = raw.get("source_type", "news")
        score = trust_score(source_type)
        text = " ".join(str(raw.get(k, "")) for k in ["title", "summary", "raw_text"])
        status = normalize_samsung_status(raw.get("samsung_status"), text)
        item = EvidenceItem(
            compressor_type=ctype,
            competitor=competitor,
            refrigerant=extract_refrigerants(raw.get("refrigerants"), text),
            category=normalize_category(raw.get("category", "신제품·라인업")),
            samsung_status=status,
            trust_score=score,
            source_type=source_type,
            threat_level=threat_level(status, score),
            week_id=week_id,
            source_url=raw.get("source_url", ""),
            source_date=raw.get("source_date", "확인필요"),
            raw_text=raw.get("raw_text") or raw.get("summary", ""),
            product_or_series=raw.get("title", "확인필요"),
            source_name=raw.get("title", raw.get("source_url", "source")),
            is_primary=competitor in PRIMARY_COMPETITORS.get(ctype, []),
            low_confidence=score < 3 or (status == "미보유" and score == 3),
            dynamic_tags=[],
        )
        candidates.append(EvidenceItem(**{**item.to_dict(), "dynamic_tags": dynamic_tags(raw, item)}))

    deduped: dict[tuple[str, str, str], EvidenceItem] = {}
    for item in candidates:
        key = (item.competitor, item.category, item.week_id)
        current = deduped.get(key)
        if current is None or item.trust_score > current.trust_score:
            deduped[key] = item
    return list(deduped.values())


def save_evidence(items: list[EvidenceItem], week_id: str, output_dir: str | Path = "outputs/evidence") -> Path:
    path = Path(output_dir) / f"{week_id}_evidence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"week_id": week_id, "evidence": [item.to_dict() for item in items]}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
