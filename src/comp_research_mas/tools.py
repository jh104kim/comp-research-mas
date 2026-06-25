from __future__ import annotations

import re

from .evidence_normalizer import extract_refrigerants, normalize_competitor, normalize_samsung_status, threat_level, trust_score
from .models import CATEGORIES, EvidenceItem, PRIMARY_COMPETITORS

HEADER_RE = re.compile(r"^\[(?P<ctype>Re|Ro|Sc)\s*-\s*(?P<competitor>[^\]]+?)\]\s*(?P<star>★)?\s*$")


def infer_category(text: str) -> str:
    lowered = text.lower()
    if any(k in text for k in ["인증", "UL", "CE", "ENERGY STAR"]):
        return "규격·인증"
    if any(k in text for k in ["로드맵", "양산", "기술", "특허", "논문"]):
        return "특허·기술"
    if any(k in text for k in ["COP", "EER", "효율", "냉동능력"]):
        return "성능·효율"
    if any(k in text for k in ["R290", "R600a", "R134a", "R1234yf", "R32", "R454B", "R454C", "R410A", "R466A", "냉매"]):
        return "신냉매·냉매전환"
    if any(k in lowered for k in ["expo", "ahr", "chillventa", "전시회", "발표"]):
        return "전시회·발표"
    return "신제품·라인업"


def infer_source(block: str) -> tuple[str, str, str, str]:
    for line in block.splitlines():
        if line.strip().startswith("출처:"):
            raw = line.split(":", 1)[1].strip()
            parts = [p.strip() for p in raw.rsplit(",", 1)]
            name = parts[0]
            date = parts[1] if len(parts) == 2 else "확인필요"
            return name, "manual://" + name.replace(" ", "-"), date, "trade_media"
    return "수동 입력", "manual://step1", "확인필요", "news"


def parse_step1_raw_data(raw_data: str, week_id: str = "2026-26") -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    current_header: re.Match[str] | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_header, current_lines
        if current_header is None:
            return
        ctype = current_header.group("ctype")
        competitor = normalize_competitor(current_header.group("competitor"))
        block = "\n".join(current_lines).strip()
        source_name, source_url, source_date, source_type = infer_source(block)
        summary_lines = [line.strip() for line in current_lines if line.strip() and not line.strip().startswith("출처:")]
        summary = " ".join(summary_lines)
        is_primary = competitor in PRIMARY_COMPETITORS.get(ctype, []) or bool(current_header.group("star"))
        status = normalize_samsung_status(None, block)
        score = trust_score(source_type)
        items.append(
            EvidenceItem(
                compressor_type=ctype,
                competitor=competitor,
                raw_text=summary,
                samsung_status=status,
                category=infer_category(block),
                product_or_series=summary_lines[0].split(".")[0] if summary_lines else "확인필요",
                refrigerant=extract_refrigerants(None, block),
                source_name=source_name,
                source_url=source_url,
                source_date=source_date,
                source_type=source_type,
                trust_score=score,
                threat_level=threat_level(status, score),
                week_id=week_id,
                is_primary=is_primary,
                low_confidence=score < 3,
                dynamic_tags=[ctype, infer_category(block), *(r for r in extract_refrigerants(None, block) if r != "확인필요")],
            )
        )
        current_header = None
        current_lines = []

    for line in raw_data.splitlines():
        match = HEADER_RE.match(line.strip())
        if match:
            flush()
            current_header = match
            current_lines = []
        elif current_header is not None:
            current_lines.append(line)
    flush()
    return items


def evidence_to_dicts(items: list[EvidenceItem]) -> list[dict]:
    return [item.to_dict() for item in items]


def categories() -> tuple[str, ...]:
    return CATEGORIES
