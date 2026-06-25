# C&M 압축기 경쟁사 모니터링 MAS

C&M 압축기 경쟁사 모니터링 Multi-Agent System(MAS) 프로젝트입니다.

목표:
- 경쟁사 신제품, 스펙, 특허, 업계 동향을 주간 단위로 수집
- R290 Reciprocating, R454B Scroll, Rotary 중심으로 분석
- Samsung Gap 관점으로 요약
- 주간 리포트를 Markdown으로 생성하고, 향후 이메일/Obsidian으로 자동 전달

현재 구현 단계:
- Phase 1 MVP: Writer + Critic self-refine 루프
- 입력: 수동 검색 결과 Markdown
- 출력: 주간 리포트 Markdown + Critic 평가 JSON

## 빠른 실행

```bash
cd /mnt/f/ai-app-dev/10-comp-research-mas
uv run python -m comp_research_mas.cli run-sample
```

결과:
- `outputs/reports/sample-weekly-report.md`
- `outputs/reports/sample-critic-review.json`

## Windows 경로

```text
F:i-app-dev-comp-research-mas
```

## WSL 경로

```text
/mnt/f/ai-app-dev/10-comp-research-mas
```

## 주요 문서

- `docs/PROJECT_PLAN.md` - 프로젝트 단계별 계획
- `docs/MAS_SPEC.md` - MAS 역할/흐름 정의
- `docs/PHASE1_MVP.md` - 1단계 Writer+Critic MVP 상세
