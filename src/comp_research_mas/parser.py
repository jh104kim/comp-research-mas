from __future__ import annotations

from pathlib import Path

from .models import SearchItem


def parse_manual_search_results(path: str | Path) -> list[SearchItem]:
    text = Path(path).read_text(encoding="utf-8")
    blocks = [b.strip() for b in text.split("### Item") if b.strip()]
    items: list[SearchItem] = []
    for block in blocks:
        fields: dict[str, str] = {}
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("-") or ":" not in line:
                continue
            key, value = line[1:].split(":", 1)
            fields[key.strip()] = value.strip()
        if "competitor" not in fields:
            continue
        items.append(
            SearchItem(
                competitor=fields.get("competitor", "Unknown"),
                product=fields.get("product", "Unknown"),
                refrigerant=fields.get("refrigerant", "Unknown"),
                compressor_type=fields.get("type", fields.get("compressor_type", "Unknown")),
                source_url=fields.get("source_url", ""),
                source_date=fields.get("source_date", ""),
                summary=fields.get("summary", ""),
                samsung_gap_note=fields.get("samsung_gap_note", ""),
            )
        )
    return items
