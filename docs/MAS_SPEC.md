# MAS SPEC

## Agents

1. Query Planner
2. Research Adapter
3. Evidence Normalizer
4. Analyst
5. Writer
6. Critic
7. Notifier/Live Sender
8. Guardian

## Data Flow

query_plan -> raw_results -> evidence -> analysis_bundle -> report -> critic_review -> guardian -> notifier/live_sender

## Core Schemas

- EvidenceItem: compressor_type, competitor, refrigerant, category, samsung_status, trust_score, source_type, threat_level, period_id, source_url, modality, extraction_confidence, source_page
- AnalysisBundle: gap_matrix, threat_summary, new_signals
- DebateRound: issue, critic_position, writer_response, decision, applied_section, before_score, after_score

## Quality Gates

- evidence threshold: exhibition=8, backfill=4, normal=6
- critic total score: 10
- hard_fail on missing source/structure/primary coverage severe failure
- guardian block patterns prevent live publishing
