import json
from pathlib import Path

from comp_research_mas.alert import detect_high_threat_alerts
from comp_research_mas.debate import run_debate_rounds
from comp_research_mas.llm_adapter import llm_dry_run
from comp_research_mas.models import EvidenceItem
from comp_research_mas.multimodal import parse_ocr_text, parse_pdf_catalog
from comp_research_mas.orchestrability import validate_runtime_config
from comp_research_mas.vector_store import ChromaVectorStore, FileVectorStore
from comp_research_mas.agents import write_step_report


def _items():
    return [
        EvidenceItem(compressor_type="Re", competitor="GMCC/Midea", refrigerant=["R290"], category="신제품·라인업", samsung_status="미보유", trust_score=5, source_type="official", threat_level="high", source_url="https://www.gmcc.com", raw_text="R290 high threat", period_id="2026-06").to_dict(),
        EvidenceItem(compressor_type="Ro", competitor="LG", refrigerant=["R32"], category="성능·효율", samsung_status="대응중", trust_score=5, source_type="official", source_url="https://www.lg.com", raw_text="rotary R32", period_id="2026-06").to_dict(),
    ]


def test_chroma_vector_store_smoke(tmp_path):
    store = ChromaVectorStore(tmp_path / "chroma")
    assert store.add_evidence(_items()) == 2
    rows = store.search("R290 GMCC", top_k=1)
    assert rows and rows[0]["competitor"] == "GMCC/Midea"
    assert (tmp_path / "chroma" / "index.json").exists()


def test_file_vector_store_fallback():
    ledger = {"periods": {"2026-06": {"evidence": _items()}}}
    rows = FileVectorStore(ledger).search(compressor_type="Ro", competitor="LG", category="성능·효율")
    assert rows and rows[0]["compressor_type"] == "Ro"


def test_debate_round_records_improvement_or_review():
    evidence = _items()
    draft = "# bad"
    result = run_debate_rounds(draft, evidence)
    assert "debate_rounds" in result
    assert isinstance(result["human_review_flag"], bool)


def test_high_threat_alert_dry_run_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parents[1])
    result = detect_high_threat_alerts(_items(), period_id="2099-01")
    assert result["count"] >= 1
    assert Path(result["slack_payload_path"]).exists()


def test_yaml_orchestrability_config_valid():
    result = validate_runtime_config()
    assert result["valid"] is True
    assert "Ro" in result["compressor_types"]["types"]


def test_llm_adapter_dry_run():
    assert llm_dry_run("stub")["provider"] == "stub"
    assert llm_dry_run("claude")["dry_run"] is True


def test_multimodal_pdf_and_ocr_evidence():
    pdf_item = parse_pdf_catalog("tests/fixtures/sample_catalog.pdf", period_id="2026-06")
    assert pdf_item.modality == "pdf"
    assert "R32" in pdf_item.refrigerant
    ocr_item = parse_ocr_text("booth image scroll compressor R454B", period_id="2026-06")
    assert ocr_item.modality == "image"
    assert "R454B" in ocr_item.refrigerant
