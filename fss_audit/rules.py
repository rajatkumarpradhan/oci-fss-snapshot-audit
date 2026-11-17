"""FSS001-FSS004 rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .model import MATURE_DAYS, STALE_DAYS


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # HIGH | MEDIUM | LOW
    fs: str
    detail: str


def rule_prod_without_snapshots(fss: tuple, as_of: date) -> list:
    """FSS001 HIGH: prod-tier file system with zero snapshots."""
    del as_of
    return [
        Finding("FSS001", "HIGH", f.display_name,
                "tagged tier=prod but has zero snapshots; production data has no recovery point")
        for f in fss if f.is_prod() and not f.snapshots
    ]


def rule_stale_recovery_point(fss: tuple, as_of: date) -> list:
    """FSS002 MEDIUM: newest snapshot older than STALE_DAYS."""
    out = []
    for f in fss:
        newest = f.newest_snapshot()
        if newest is not None and (as_of - newest.created_at).days > STALE_DAYS:
            out.append(
                Finding("FSS002", "MEDIUM", f.display_name,
                        f"newest snapshot '{newest.name}' is {(as_of - newest.created_at).days} days old "
                        f"(> {STALE_DAYS}); the recovery point is stale")
            )
    return out


def rule_mature_without_snapshots(fss: tuple, as_of: date) -> list:
    """FSS003 MEDIUM: any-tier file system older than MATURE_DAYS with zero snapshots."""
    return [
        Finding("FSS003", "MEDIUM", f.display_name,
                f"{f.age_days(as_of)} days old (> {MATURE_DAYS}) with zero snapshots; "
                f"no longer a throwaway, still no recovery point")
        for f in fss if not f.snapshots and f.age_days(as_of) > MATURE_DAYS
    ]


def rule_unowned(fss: tuple, as_of: date) -> list:
    """FSS004 LOW: no owner tag."""
    del as_of
    return [
        Finding("FSS004", "LOW", f.display_name,
                "no 'owner' tag; nobody is accountable for its recovery plan")
        for f in fss if not str(f.tags.get("owner", "")).strip()
    ]


ALL_RULES = (
    rule_prod_without_snapshots,
    rule_stale_recovery_point,
    rule_mature_without_snapshots,
    rule_unowned,
)

_SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def run_all(fss: tuple, as_of: date) -> list:
    findings = []
    for rule in ALL_RULES:
        findings.extend(rule(fss, as_of))
    findings.sort(key=lambda x: (_SEVERITY_RANK[x.severity], x.rule, x.fs))
    return findings


def exit_code(findings: list) -> int:
    if any(f.severity == "HIGH" for f in findings):
        return 2
    if findings:
        return 1
    return 0
