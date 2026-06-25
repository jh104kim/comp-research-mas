from __future__ import annotations

import argparse
from pathlib import Path

from .graph import run_step1
from .pipeline import run_writer_critic_loop


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C&M compressor research MAS")
    sub = parser.add_subparsers(dest="command", required=True)

    sample = sub.add_parser("run-sample", help="Run legacy Phase 1 Writer+Critic loop with sample input")
    sample.add_argument("--week-label", default="sample")

    step1 = sub.add_parser("run-step1-sample", help="Run STEP 1 LangGraph Writer+Critic self-refine sample")
    step1.add_argument("--input-path", default="examples/manual_search_results/step1_raw_data.md")

    run = sub.add_parser("run", help="Run legacy Phase 1 with a manual search results markdown file")
    run.add_argument("input_path")
    run.add_argument("--output-dir", default="outputs/reports")
    run.add_argument("--week-label", default="manual")

    args = parser.parse_args(argv)
    if args.command == "run-sample":
        input_path = Path("examples/manual_search_results/sample_2026w26.md")
        report, review = run_writer_critic_loop(input_path, "outputs/reports", week_label=args.week_label)
        print(f"report_title={report.title}")
        print(f"critic_score={review.score}")
        print(f"critic_passed={review.passed}")
        return 0

    if args.command == "run-step1-sample":
        raw_data = Path(args.input_path).read_text(encoding="utf-8")
        state = run_step1(raw_data)
        print("step=STEP1")
        print(f"status={state.get('status')}")
        print(f"critic_score={state.get('score')}")
        print(f"iteration={state.get('iteration')}")
        print(f"hard_fail={state.get('hard_fail')}")
        for key, value in state.get("output_paths", {}).items():
            print(f"{key}_path={value}")
        return 0 if not state.get("hard_fail") else 2

    report, review = run_writer_critic_loop(args.input_path, args.output_dir, week_label=args.week_label)
    print(f"report_title={report.title}")
    print(f"critic_score={review.score}")
    print(f"critic_passed={review.passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
