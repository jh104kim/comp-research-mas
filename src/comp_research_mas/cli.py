from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import run_writer_critic_loop


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C&M compressor research MAS")
    sub = parser.add_subparsers(dest="command", required=True)

    sample = sub.add_parser("run-sample", help="Run Phase 1 Writer+Critic loop with sample input")
    sample.add_argument("--week-label", default="sample")

    run = sub.add_parser("run", help="Run Phase 1 with a manual search results markdown file")
    run.add_argument("input_path")
    run.add_argument("--output-dir", default="outputs/reports")
    run.add_argument("--week-label", default="manual")

    args = parser.parse_args(argv)
    if args.command == "run-sample":
        input_path = Path("examples/manual_search_results/sample_2026w26.md")
        report, review = run_writer_critic_loop(input_path, "outputs/reports", week_label=args.week_label)
    else:
        report, review = run_writer_critic_loop(args.input_path, args.output_dir, week_label=args.week_label)

    print(f"report_title={report.title}")
    print(f"critic_score={review.score}")
    print(f"critic_passed={review.passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
