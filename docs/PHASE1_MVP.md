# Phase 1 MVP — Writer + Critic Loop

## 목표

외부 검색 자동화 없이, 삿뽀로가 수동으로 붙여넣은 검색 결과를 주간 리포트로 만들고 Critic이 품질을 검토한다.

## 입력 형식

`examples/manual_search_results/*.md` 파일에 아래 섹션을 둔다.

```markdown
# Manual Search Results

## Items

### Item 1
- competitor: Secop
- product: KL / NL / DL
- refrigerant: R290
- type: Reciprocating
- source_url: https://example.com
- source_date: 2026-06-25
- summary: ...
- samsung_gap_note: ...
```

## 출력 형식

- Markdown 리포트: `outputs/reports/*.md`
- Critic 평가: `outputs/reports/*.json`

## Critic 기준

총점 100점:
- 출처 명시: 25
- 경쟁사 커버리지: 25
- Samsung Gap 관점: 25
- 가독성/분량: 25

80점 미만이면 Writer refine 대상이다.
