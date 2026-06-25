from comp_research_mas.special_report import generate_special_report, load_special_dataset


def test_special_report_dataset_and_outputs():
    dataset = load_special_dataset()
    assert len(dataset["groups"]["2025 H2"]) > 0
    assert len(dataset["groups"]["2026 H1"]) > 0
    summary = generate_special_report()
    assert summary["total_evidence"] >= 100
    assert summary["counts"]["2025 H2"] > 0
    assert summary["counts"]["2026 H1"] > 0
    assert "Re" in summary["by_compressor_type"]
