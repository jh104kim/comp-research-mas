from pathlib import Path

from comp_research_mas.parser import parse_manual_search_results
from comp_research_mas.pipeline import run_writer_critic_loop


def test_parse_manual_search_results_sample():
    items = parse_manual_search_results("examples/manual_search_results/sample_2026w26.md")
    assert len(items) == 4
    assert items[0].competitor == "Secop"
    assert "R290" in items[0].refrigerant


def test_writer_critic_loop_creates_outputs(tmp_path: Path):
    report, review = run_writer_critic_loop(
        "examples/manual_search_results/sample_2026w26.md",
        tmp_path,
        week_label="test-week",
    )
    assert "C&M 압축기 경쟁사 주간 모니터링 리포트" in report.markdown
    assert "Samsung Gap" in report.markdown
    assert review.score >= 70
    assert (tmp_path / "test-week-weekly-report.md").exists()
    assert (tmp_path / "test-week-critic-review.json").exists()
