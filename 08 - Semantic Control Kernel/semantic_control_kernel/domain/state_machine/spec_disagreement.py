from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

from semantic_control_kernel.domain.state_machine.models import StateSpecDisagreement, TransitionRule
from semantic_control_kernel.domain.state_machine.transition_table import TRANSITION_RULES


CLAIM_PATTERNS = {
    "required_state": re.compile(r"^\s*[-*]?\s*Required State\s*:\s*(?P<claim>.+?)\s*$", re.IGNORECASE),
    "post_state": re.compile(r"^\s*[-*]?\s*Post-State\s*:\s*(?P<claim>.+?)\s*$", re.IGNORECASE),
    "confirmation_gate": re.compile(r"^\s*[-*]?\s*(?:User Confirmation|Confirmation)\s*:\s*(?P<claim>.+?)\s*$", re.IGNORECASE),
}


def detect_workflow_spec_disagreements(
    workflow_specs: Mapping[str, str | Path],
    transition_rules: tuple[TransitionRule, ...] = TRANSITION_RULES,
) -> tuple[StateSpecDisagreement, ...]:
    rule_by_name = {rule.function_or_route: rule for rule in transition_rules}
    disagreements: list[StateSpecDisagreement] = []
    for spec_name, text_or_path in workflow_specs.items():
        text = _read_text(text_or_path)
        for route, section in _sections_by_route(text, tuple(rule_by_name)):
            rule = rule_by_name[route]
            for claim_kind, claim in _explicit_claims(section):
                state_table_claim = _rule_claim(rule, claim_kind)
                if _normalize_claim(claim) == _normalize_claim(state_table_claim):
                    continue
                disagreements.append(
                    StateSpecDisagreement(
                        workflow_spec=spec_name,
                        workflow_route=route,
                        step_name=claim_kind,
                        state_table_rule_id=rule.rule_id,
                        workflow_claim=claim,
                        state_table_claim=state_table_claim,
                        required_correction="Update workflow checklist text to match 02_kernel_state_transition_table.md.",
                    )
                )
    return tuple(disagreements)


def _read_text(value: str | Path) -> str:
    if isinstance(value, Path):
        return value.read_text(encoding="utf-8")
    possible = Path(value)
    if possible.exists():
        return possible.read_text(encoding="utf-8")
    return value


def _sections_by_route(text: str, routes: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    lines = text.splitlines()
    route_set = set(routes)
    sections: list[tuple[str, str]] = []
    current_route: str | None = None
    current_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped in route_set:
            if current_route is not None:
                sections.append((current_route, "\n".join(current_lines)))
            current_route = stripped
            current_lines = []
            continue
        if current_route is not None:
            if stripped in route_set:
                sections.append((current_route, "\n".join(current_lines)))
                current_route = stripped
                current_lines = []
            else:
                current_lines.append(line)
    if current_route is not None:
        sections.append((current_route, "\n".join(current_lines)))
    return tuple(sections)


def _explicit_claims(section: str) -> tuple[tuple[str, str], ...]:
    claims = []
    for line in section.splitlines():
        for claim_kind, pattern in CLAIM_PATTERNS.items():
            match = pattern.match(line)
            if match:
                claims.append((claim_kind, match.group("claim").strip()))
    return tuple(claims)


def _rule_claim(rule: TransitionRule, claim_kind: str) -> str:
    if claim_kind == "required_state":
        return rule.required_state_text
    if claim_kind == "post_state":
        return rule.post_state_text
    if claim_kind == "confirmation_gate":
        return rule.confirmation_gate
    raise ValueError(f"Unknown claim kind: {claim_kind}")


def _normalize_claim(value: str) -> str:
    text = value.strip().casefold()
    text = text.replace("user_confirmation required", "destructive")
    text = text.replace("yes if overwrite", "overwrite_only")
    text = text.replace("yes when destructive", "destructive_when_projection_removal")
    text = text.replace("yes", "destructive")
    text = text.replace("no", "none")
    text = re.sub(r"\s+", " ", text)
    return text
