from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .agents import critique_step_report, write_step_report
from .models import EvidenceItem


@dataclass(frozen=True)
class DebateRound:
    issue: str
    critic_position: str
    writer_response: str
    decision: str
    applied_section: str
    before_score: float
    after_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_debate_rounds(draft: str, evidence_dicts: list[dict[str, Any]], *, analysis_bundle: dict[str, Any] | None = None, max_minor: int = 1, max_major: int = 2) -> dict[str, Any]:
    before = critique_step_report(draft, evidence_dicts, analysis_bundle=analysis_bundle)
    minor_used = major_used = 0
    rounds: list[DebateRound] = []
    current_draft = draft
    for point in before.get("debate_points", []):
        severity = point.get("severity", "minor")
        if severity == "minor" and minor_used >= max_minor:
            continue
        if severity == "major" and major_used >= max_major:
            continue
        if severity == "minor":
            minor_used += 1
        else:
            major_used += 1
        directives = [point.get("suggestion") or point.get("issue") or "근거 기반 보강"]
        items = [EvidenceItem(**item) for item in evidence_dicts]
        rewritten = write_step_report(items, analysis_bundle=analysis_bundle, writer_directives=directives)
        after = critique_step_report(rewritten, evidence_dicts, analysis_bundle=analysis_bundle)
        accepted = after["score"] >= before["score"]
        rounds.append(DebateRound(
            issue=point.get("issue", "unknown"),
            critic_position=point.get("suggestion", "보강 필요"),
            writer_response="writer_directives 기반 섹션 재작성" if accepted else "재작성했으나 점수 개선 없음",
            decision="accepted" if accepted else "rejected",
            applied_section=point.get("section", "unknown"),
            before_score=before["score"],
            after_score=after["score"],
        ))
        if accepted:
            current_draft = rewritten
            before = after
        else:
            break
    return {"draft": current_draft, "review": before, "debate_rounds": [r.to_dict() for r in rounds], "human_review_flag": bool(rounds and rounds[-1].decision == "rejected")}
