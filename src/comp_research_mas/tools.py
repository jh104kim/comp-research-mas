from __future__ import annotations

import re

from .models import (
    CATEGORIES,
    COMPETITOR_ALIASES,
    EvidenceItem,
    PRIMARY_COMPETITORS,
    SAMSUNG_STATUSES,
)

HEADER_RE = re.compile(r"^\[(?P<ctype>Re|Ro|Sc)\s*-\s*(?P<competitor>[^\]]+?)\]\s*(?P<star>★)?\s*$")


def normalize_competitor(name: str) -> str:
    clean = name.strip()
    return COMPETITOR_ALIASES.get(clean, clean)


def infer_category(text: str) -> str:
    lowered = text.lower()
    if any(k in text for k in ["인증", "UL", "CE", "ENERGY STAR"]):
        return "규격·인증"
    if any(k in text for k in ["로드맵", "양산", "기술", "특허", "논문"]):
        return "특허·기술"
    if any(k in text for k in ["COP", "EER", "효율", "냉동능력"]):
        return "성능·효율"
    if any(k in text for k in ["R290", "R600a", "R134a", "R1234yf", "R32", "R454B", "R454C", "R410A", "R466A", "냉매"]):
        return "신냉매·냉매 전환"
    if any(k in lowered for k in ["expo", "ahr", "chillventa", "전시회", "발표"]):
        return "전시회·발표"
    return "신제품·라인업"


def infer_samsung_status(text: str) -> str:
    # Order matters: "미보유" contains "보유" as a substring.
    for status in ("미보유", "대응 중", "확인 필요", "보유"):
        if status in text:
            return status
    if "미대응" in text or "부재" in text:
        return "미보유"
    return "확인 필요"


def infer_refrigerant(text: str) -> str:
    found = []
    for ref in ["R290", "R600a", "R134a", "R1234yf", "R32", "R454B", "R454C", "R410A", "R466A"]:
        if ref in text:
            found.append(ref)
    return "/".join(found) if found else "확인 필요"


def infer_source(block: str) -> tuple[str, str, str]:
    for line in block.splitlines():
        if line.strip().startswith("출처:"):
            raw = line.split(":", 1)[1].strip()
            parts = [p.strip() for p in raw.rsplit(",", 1)]
            if len(parts) == 2:
                return parts[0], "manual://" + parts[0].replace(" ", "-"), parts[1]
            return raw, "manual://" + raw.replace(" ", "-"), "확인 필요"
    return "수동 입력", "manual://step1", "확인 필요"


def parse_step1_raw_data(raw_data: str) -> list[EvidenceItem]:
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
        source_name, source_url, source_date = infer_source(block)
        summary_lines = [line.strip() for line in current_lines if line.strip() and not line.strip().startswith("출처:")]
        summary = " ".join(summary_lines)
        is_primary = competitor in PRIMARY_COMPETITORS.get(ctype, []) or bool(current_header.group("star"))
        items.append(
            EvidenceItem(
                compressor_type=ctype,
                competitor=competitor,
                summary=summary,
                samsung_status=infer_samsung_status(block),
                category=infer_category(block),
                product_or_series=summary_lines[0].split(".")[0] if summary_lines else "확인 필요",
                refrigerant=infer_refrigerant(block),
                source_name=source_name,
                source_url=source_url,
                source_date=source_date,
                trust_score=4 if source_name != "수동 입력" else 3,
                is_primary=is_primary,
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
