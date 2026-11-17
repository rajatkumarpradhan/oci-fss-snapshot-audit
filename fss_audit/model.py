"""Data model + export loading for the FSS snapshot audit."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime


class ExportError(ValueError):
    """Raised when an export file is malformed."""


STALE_DAYS = 7
MATURE_DAYS = 30


def parse_date(value: str, what: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ExportError(f"invalid date for {what}: {value!r} (expected YYYY-MM-DD)") from exc


@dataclass(frozen=True)
class Snap:
    name: str
    created_at: date


@dataclass(frozen=True)
class FileSystem:
    ocid: str
    display_name: str
    created_at: date
    tags: dict = field(default_factory=dict)
    snapshots: tuple = ()

    def newest_snapshot(self) -> Snap | None:
        if not self.snapshots:
            return None
        return max(self.snapshots, key=lambda s: s.created_at)

    def age_days(self, as_of: date) -> int:
        return (as_of - self.created_at).days

    def is_prod(self) -> bool:
        return str(self.tags.get("tier", "")).strip().lower() == "prod"


def load_export(path: str) -> tuple:
    with open(path, "r", encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ExportError(f"{path}: not valid JSON: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("file_systems"), list):
        raise ExportError(f"{path}: top level must be an object with a 'file_systems' list")
    out = []
    for i, f in enumerate(raw["file_systems"]):
        where = f"file_systems[{i}]"
        for req in ("ocid", "display_name", "created_at"):
            if req not in f:
                raise ExportError(f"{where}: missing required field {req!r}")
        snaps = []
        for j, s in enumerate(f.get("snapshots", [])):
            if "created_at" not in s:
                raise ExportError(f"{where}.snapshots[{j}]: missing required field 'created_at'")
            snaps.append(Snap(name=s.get("name", "") or "",
                              created_at=parse_date(s["created_at"], f"{where}.snapshots[{j}].created_at")))
        out.append(
            FileSystem(
                ocid=f["ocid"],
                display_name=f["display_name"],
                created_at=parse_date(f["created_at"], f"{where}.created_at"),
                tags=f.get("tags", {}) or {},
                snapshots=tuple(snaps),
            )
        )
    return tuple(out)
