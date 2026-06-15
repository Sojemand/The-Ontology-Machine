from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_SUITE_FIELDS = {
    "name",
    "display_name",
    "module",
    "kind",
    "driver",
    "inventory_gate",
    "modes",
    "sandbox",
    "cases",
}


@dataclass(frozen=True)
class Case:
    id: str
    title: str
    type: str
    risk: str
    expected_actions: tuple[str, ...]
    payload: dict[str, Any]


@dataclass(frozen=True)
class SuiteManifest:
    path: Path
    name: str
    display_name: str
    module: str
    kind: str
    driver: str
    inventory_gate: bool
    modes: tuple[str, ...]
    sandbox: dict[str, Any]
    cases: tuple[Case, ...]
    raw: dict[str, Any]


def discover_suites(suite_dir: Path) -> list[SuiteManifest]:
    suites = [load_suite(path) for path in sorted(suite_dir.glob("*.json"))]
    suites.sort(key=lambda suite: suite.name.casefold())
    return suites


def load_suite(path: Path) -> SuiteManifest:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    missing = sorted(REQUIRED_SUITE_FIELDS.difference(raw))
    if missing:
        raise ValueError(f"Suite manifest {path} missing required fields: {', '.join(missing)}")
    cases = tuple(_load_case(case) for case in raw.get("cases", []))
    return SuiteManifest(
        path=path,
        name=str(raw["name"]),
        display_name=str(raw["display_name"]),
        module=str(raw["module"]),
        kind=str(raw["kind"]),
        driver=str(raw["driver"]),
        inventory_gate=bool(raw["inventory_gate"]),
        modes=tuple(str(value) for value in raw.get("modes", [])),
        sandbox=dict(raw.get("sandbox", {})),
        cases=cases,
        raw=raw,
    )


def select_suites(suites: list[SuiteManifest], selector: str) -> list[SuiteManifest]:
    if selector == "all":
        return suites
    matches = [
        suite
        for suite in suites
        if selector.casefold()
        in {suite.name.casefold(), suite.display_name.casefold(), suite.module.casefold()}
    ]
    if len(matches) == 1:
        return matches
    partial = [
        suite
        for suite in suites
        if selector.casefold() in suite.name.casefold()
        or selector.casefold() in suite.display_name.casefold()
        or selector.casefold() in suite.module.casefold()
    ]
    if len(partial) == 1:
        return partial
    if not partial:
        raise ValueError(f"Unknown suite selector: {selector}")
    raise ValueError(f"Ambiguous suite selector: {selector}")


def validate_suite(suite: SuiteManifest) -> list[str]:
    errors: list[str] = []
    if not suite.cases:
        errors.append("suite has no cases")
    if "deterministic" not in suite.modes:
        errors.append("suite does not declare deterministic mode")
    if not isinstance(suite.sandbox, dict):
        errors.append("sandbox must be an object")
    case_ids: set[str] = set()
    for case in suite.cases:
        if case.id in case_ids:
            errors.append(f"duplicate case id: {case.id}")
        case_ids.add(case.id)
        if not case.expected_actions and case.type in {"button_action", "workflow"}:
            errors.append(f"case {case.id} has no expected_actions")
    return errors


def _load_case(raw: dict[str, Any]) -> Case:
    for field in ("id", "title", "type", "risk"):
        if field not in raw:
            raise ValueError(f"Case missing required field: {field}")
    return Case(
        id=str(raw["id"]),
        title=str(raw["title"]),
        type=str(raw["type"]),
        risk=str(raw["risk"]),
        expected_actions=tuple(str(value) for value in raw.get("expected_actions", [])),
        payload=raw,
    )
