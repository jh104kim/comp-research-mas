from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import EvidenceItem


def parse_pdf_catalog(path: str | Path, *, period_id: str = "2026-06") -> EvidenceItem:
    p = Path(path)
    data = p.read_bytes()
    text = data.decode("latin-1", errors="ignore")
    marker = re.search(r"COMP_RESEARCH_TEXT:(.*?)(?:END_COMP_RESEARCH_TEXT|$)", text, re.S)
    extracted = marker.group(1).strip() if marker else p.stem
    refs = re.findall(r"R\d{2,4}[A-Za-z]?", extracted) or ["확인필요"]
    ctype = "Ro" if "rotary" in extracted.lower() else "Sc" if "scroll" in extracted.lower() else "Re"
    return EvidenceItem(
        compressor_type=ctype,
        competitor="멀티모달/PDF",
        refrigerant=refs,
        category="신제품·라인업",
        samsung_status="확인필요",
        trust_score=4,
        source_type="academic",
        week_id=period_id,
        period_id=period_id,
        source_url=f"file://{p}",
        source_date="확인필요",
        raw_text=extracted,
        summary=extracted[:300],
        product_or_series=p.name,
        source_name=p.name,
        dynamic_tags=["pdf", "multimodal"],
        modality="pdf",
        extraction_confidence=0.75 if marker else 0.4,
        source_page="1",
    )


def parse_ocr_text(text: str, *, source_name: str = "sample_ocr", period_id: str = "2026-06") -> EvidenceItem:
    refs = re.findall(r"R\d{2,4}[A-Za-z]?", text) or ["확인필요"]
    return EvidenceItem(
        compressor_type="Ro" if "rotary" in text.lower() else "Sc" if "scroll" in text.lower() else "Re",
        competitor="멀티모달/OCR",
        refrigerant=refs,
        category="전시회·발표",
        trust_score=3,
        source_type="trade_media",
        week_id=period_id,
        period_id=period_id,
        source_url=f"manual://ocr/{source_name}",
        raw_text=text,
        summary=text[:300],
        source_name=source_name,
        dynamic_tags=["image", "ocr", "multimodal"],
        modality="image",
        extraction_confidence=0.65,
        source_page="image-1",
    )
