from __future__ import annotations

import json
from pathlib import Path

from .critic import review_report
from .models import CriticReview, WeeklyReport
from .parser import parse_manual_search_results
from .writer import write_weekly_report


def run_writer_critic_loop(input_path: str | Path, output_dir: str | Path, *, week_label: str = "sample", max_revisions: int = 2) -> tuple[WeeklyReport, CriticReview]:
    items = parse_manual_search_results(input_path)
    feedback: list[str] = []
    review: CriticReview | None = None
    report: WeeklyReport | None = None

    for revision in range(max_revisions + 1):
        report = write_weekly_report(items, week_label=week_label, revision=revision, critic_feedback=feedback)
        review = review_report(report)
        if review.passed:
            break
        feedback = review.required_fixes

    assert report is not None and review is not None
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / f"{week_label}-weekly-report.md"
    review_path = output / f"{week_label}-critic-review.json"
    report_path.write_text(report.markdown, encoding="utf-8")
    review_path.write_text(json.dumps(review.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return report, review
