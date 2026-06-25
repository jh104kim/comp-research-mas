from __future__ import annotations

import argparse
from pathlib import Path

from .graph import run_step1, run_step2, run_step3, run_step5, run_step6
from .orchestrator import run_monthly_orchestrator
from .pipeline import run_writer_critic_loop
from .scheduler import run_monthly
from .backfill_planner import run_backfill


def _print_state(state: dict) -> int:
    print(f"status={state.get('status')}")
    print(f"period_id={state.get('period_id')}")
    print(f"critic_score={state.get('score')}")
    print(f"iteration={state.get('iteration')}")
    print(f"hard_fail={state.get('hard_fail')}")
    print(f"auto_publish_blocked={bool(state.get('auto_publish_blocked', False))}")
    meta = state.get("report_meta") or {}
    if meta:
        print(f"evidence_count={meta.get('total_evidence_count')}")
        print(f"high_threat_count={meta.get('high_threat_count')}")
        print(f"signal_count={meta.get('signal_count')}")
    if state.get("reasoning_log") is not None:
        print(f"reasoning_log_count={len(state.get('reasoning_log', []))}")
    for key, value in state.get("output_paths", {}).items():
        print(f"{key}_path={value}")
    return 0 if not state.get("hard_fail") else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C&M compressor research MAS")
    sub = parser.add_subparsers(dest="command", required=True)

    sample = sub.add_parser("run-sample", help="Run legacy Phase 1 Writer+Critic loop with sample input")
    sample.add_argument("--week-label", default="sample")

    step1 = sub.add_parser("run-step1-sample", help="Run STEP 1 LangGraph Writer+Critic self-refine sample")
    step1.add_argument("--input-path", default="examples/manual_search_results/step1_raw_data.md")

    step2 = sub.add_parser("run-step2-sample", help="Run STEP 2 Search Agent stub E2E")
    step2.add_argument("--week-id", default="2026-26")

    step3 = sub.add_parser("run-step3-sample", help="Run STEP 3 Analyst Agent stub E2E")
    step3.add_argument("--week-id", default="2026-26")

    step4 = sub.add_parser("run-step4-sample", help="Run STEP 4 monthly orchestrator sample")
    step4.add_argument("--period-id", default="2026-06")

    monthly = sub.add_parser("run-monthly", help="Run monthly scheduler; use --manual for event/manual trigger")
    monthly.add_argument("--period-id", default=None)
    monthly.add_argument("--manual", action="store_true")

    step5 = sub.add_parser("run-step5-sample", help="Run STEP 5 graph with Hermes adapter stub/injected mode and notifier dry-run")
    step5.add_argument("--period-id", default="2026-06")
    step5.add_argument("--injected-results-path", default=None)

    step5_live = sub.add_parser("run-step5-live", help="Run STEP 5 live-shaped command; dry-run unless --approve-send")
    step5_live.add_argument("--period-id", default="2026-06")
    step5_live.add_argument("--injected-results-path", default=None)
    step5_live.add_argument("--approve-send", action="store_true")

    step6 = sub.add_parser("run-step6-sample", help="Run STEP 6 graph with auto-approver and live sender dry-run")
    step6.add_argument("--period-id", default="2026-06")
    step6.add_argument("--injected-results-path", default=None)

    step6_live = sub.add_parser("run-step6-live", help="Run STEP 6 live: actual send only when auto-approved")
    step6_live.add_argument("--period-id", default="2026-06")
    step6_live.add_argument("--injected-results-path", default=None)


    backfill = sub.add_parser("run-backfill", help="Run monthly backfill dry-run for 2025 H2~2026 periods")
    backfill.add_argument("--from-period", default="2025-07")
    backfill.add_argument("--to-period", default="2026-06")
    backfill.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)

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
        print("step=STEP1")
        return _print_state(run_step1(raw_data))
    if args.command == "run-step2-sample":
        print("step=STEP2")
        return _print_state(run_step2(args.week_id))
    if args.command == "run-step3-sample":
        print("step=STEP3")
        return _print_state(run_step3(args.week_id))
    if args.command == "run-step4-sample":
        print("step=STEP4")
        return _print_state(run_monthly_orchestrator(period_id=args.period_id, manual=True))
    if args.command == "run-monthly":
        print("step=MONTHLY")
        return _print_state(run_monthly(period_id=args.period_id, manual=args.manual))
    if args.command == "run-step5-sample":
        print("step=STEP5")
        return _print_state(run_step5(period_id=args.period_id, injected_results_path=args.injected_results_path, approve_send=False))
    if args.command == "run-step5-live":
        print("step=STEP5_LIVE")
        if not args.approve_send:
            print("approve_send=False: STEP 5 live command remains dry-run. STEP 6에서 실제 발송 예정")
        return _print_state(run_step5(period_id=args.period_id, injected_results_path=args.injected_results_path, approve_send=args.approve_send))
    if args.command == "run-step6-sample":
        print("step=STEP6")
        return _print_state(run_step6(period_id=args.period_id, injected_results_path=args.injected_results_path, dry_run=True))
    if args.command == "run-step6-live":
        print("step=STEP6_LIVE")
        return _print_state(run_step6(period_id=args.period_id, injected_results_path=args.injected_results_path, dry_run=False))

    if args.command == "run-backfill":
        print("step=BACKFILL")
        summary = run_backfill(from_period=args.from_period, to_period=args.to_period, dry_run=args.dry_run)
        print(f"period_count={summary['period_count']}")
        print(f"latest_period={summary['latest']['period_id']}")
        for key, value in summary.get("output_paths", {}).items():
            print(f"{key}_path={value}")
        insufficient = [s["period_id"] for s in summary["period_snapshots"] if s["data_insufficient"]]
        print(f"data_insufficient_periods={','.join(insufficient)}")
        return 0

    report, review = run_writer_critic_loop(args.input_path, args.output_dir, week_label=args.week_label)
    print(f"report_title={report.title}")
    print(f"critic_score={review.score}")
    print(f"critic_passed={review.passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
