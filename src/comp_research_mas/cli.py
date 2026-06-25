from __future__ import annotations

import argparse
from pathlib import Path

from .graph import run_step1, run_step2, run_step3, run_step5, run_step6
from .orchestrator import run_monthly_orchestrator
from .pipeline import run_writer_critic_loop
from .scheduler import run_monthly
from .backfill_planner import run_backfill
from .alert import detect_high_threat_alerts
from .guardian import scan_text
from .llm_adapter import llm_dry_run
from .multimodal import parse_pdf_catalog
from .orchestrability import validate_runtime_config
from .vector_store import ChromaVectorStore


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
    backfill.add_argument("--show-query-plan", action="store_true")
    backfill.add_argument("--injected-results-path", default=None)


    vec_rebuild = sub.add_parser("rebuild-vector-store", help="Rebuild local Chroma-compatible vector store")
    vec_rebuild.add_argument("--persist-dir", default="outputs/vector_store/chroma")

    vec_search = sub.add_parser("vector-search", help="Search local vector store")
    vec_search.add_argument("query")
    vec_search.add_argument("--top-k", type=int, default=3)

    gscan = sub.add_parser("guardian-scan", help="Scan files for block/warn patterns")
    gscan.add_argument("--path", default="outputs/")

    cfg = sub.add_parser("config-validate", help="Validate yaml orchestration config")

    alert_cmd = sub.add_parser("alert-dry-run", help="Detect high threat evidence and write Slack dry-run payload")
    alert_cmd.add_argument("--period-id", default="2026-06")

    llm_cmd = sub.add_parser("llm-dry-run", help="Run provider-selected LLM adapter in dry-run")
    llm_cmd.add_argument("--provider", default=None)

    mm_cmd = sub.add_parser("parse-sample-pdf", help="Parse sample PDF into an EvidenceItem")
    mm_cmd.add_argument("--path", default="tests/fixtures/sample_catalog.pdf")
    mm_cmd.add_argument("--period-id", default="2026-06")

    run = sub.add_parser("run", help="Run legacy Phase 1 with a manual search results markdown file")
    run.add_argument("input_path")
    run.add_argument("--output-dir", default="outputs/reports")
    run.add_argument("--week-label", default="manual")

    args = parser.parse_args(argv)

    if args.command == "rebuild-vector-store":
        store = ChromaVectorStore(args.persist_dir)
        count = store.rebuild()
        print(f"vector_store=rebuild")
        print(f"count={count}")
        print(f"persist_dir={args.persist_dir}")
        return 0
    if args.command == "vector-search":
        store = ChromaVectorStore()
        if not store.records:
            store.rebuild()
        rows = store.search(args.query, top_k=args.top_k)
        print(f"matches={len(rows)}")
        for row in rows:
            print(f"{row.get('semantic_score')} {row.get('period_id')} {row.get('compressor_type')} {row.get('competitor')} {row.get('category')}")
        return 0
    if args.command == "guardian-scan":
        target = Path(args.path)
        texts = []
        files = [target] if target.is_file() else [p for p in target.rglob('*') if p.is_file()]
        for file in files:
            try:
                texts.append(file.read_text(encoding='utf-8', errors='ignore'))
            except Exception:
                continue
        result = scan_text("\n".join(texts))
        print(f"severity={result.severity}")
        print(f"block_hits={len(result.block_hits)}")
        print(f"warn_hits={len(result.warn_hits)}")
        return 0 if result.severity != 'block' else 2
    if args.command == "config-validate":
        result = validate_runtime_config()
        print(f"valid={result['valid']}")
        for err in result['errors']:
            print(f"error={err}")
        return 0 if result['valid'] else 2
    if args.command == "alert-dry-run":
        import json
        evidence_path = Path(f"outputs/evidence/{args.period_id}_evidence.json")
        payload = json.loads(evidence_path.read_text(encoding='utf-8')) if evidence_path.exists() else {"evidence": []}
        result = detect_high_threat_alerts(payload.get('evidence', []), period_id=args.period_id)
        print(f"high_threat_count={result['count']}")
        print(f"slack_payload_path={result['slack_payload_path']}")
        return 0
    if args.command == "llm-dry-run":
        result = llm_dry_run(args.provider)
        print(f"provider={result['provider']}")
        print(f"dry_run={result['dry_run']}")
        return 0
    if args.command == "parse-sample-pdf":
        item = parse_pdf_catalog(args.path, period_id=args.period_id)
        print(f"modality={item.modality}")
        print(f"compressor_type={item.compressor_type}")
        print(f"refrigerant={','.join(item.refrigerant)}")
        print(f"confidence={item.extraction_confidence}")
        return 0

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
        summary = run_backfill(from_period=args.from_period, to_period=args.to_period, dry_run=args.dry_run, injected_results_path=args.injected_results_path, show_query_plan=args.show_query_plan)
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
