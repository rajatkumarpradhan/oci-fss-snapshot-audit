# oci-fss-snapshot-audit

**Category: custom portfolio tool.** Pure Python command-line auditor. It does **not** wire any
built-in OCI services together - it is the *custom* project in its daily pair (the built-in
services project is `oci-ootb-objectstorage-replication-check`).

## The problem

A File Storage file system without snapshots has exactly one copy of your data. Teams usually
discover this during an incident, not before. The awkward part is that snapshot coverage
decays quietly: a file system created for a "quick test" becomes production, snapshots get
deleted to reclaim space, or the newest snapshot silently ages into uselessness. This tool
audits an **offline export** of file systems and their snapshots and flags the gaps.

## What it does

Reads a JSON export (schema below, synthetic samples included) and applies four rules:

| Rule | Severity | Fires when |
| ---- | -------- | ---------- |
| FSS001 | HIGH | A file system tagged `tier=prod` has zero snapshots - no recovery point at all for production data. |
| FSS002 | MEDIUM | The newest snapshot of a file system is older than 7 days - the recovery point is stale. |
| FSS003 | MEDIUM | A file system older than 30 days (any tier) has zero snapshots - it is not a throwaway anymore, and still has no recovery point. |
| FSS004 | LOW | A file system has no `owner` tag - nobody is accountable for its recovery plan. |

Exit code: `2` if any HIGH finding, `1` if only MEDIUM/LOW, `0` when clean.

## Run it

```bash
python -m fss_audit.cli samples/fss_messy.json --as-of 2026-11-18   # exits 2, all 4 rules fire
python -m fss_audit.cli samples/fss_clean.json --as-of 2026-11-18   # exits 0
python -m unittest discover -s tests -v                             # 21 tests, stdlib only
```

`--as-of` fixes the reference date so age math is reproducible; omit it for today (UTC).

## Export schema

```json
{
  "file_systems": [
    {"ocid": "ocid1.filesystem.oc1..f1", "display_name": "shared-data",
     "created_at": "2026-01-10", "tags": {"tier": "prod", "owner": "data-team"},
     "snapshots": [{"name": "daily-2026-11-17", "created_at": "2026-11-17"}]}
  ]
}
```

## Honest limits

- **Offline only**: the export is synthetic; nothing calls the OCI File Storage API.
- The 7-day staleness window (FSS002) and 30-day maturity window (FSS003) are defaults, not
  OCI policy - tune them to your RPO.
- Snapshot *existence* says nothing about snapshot *restorability*; only a restore test proves
  that, and this tool does not perform one.
- The `tier=prod` tag convention is this tool's contract, not an OCI standard.

## Project status

Built as a daily portfolio project. 21 unit tests, green locally and in CI
(`.github/workflows/ci.yml`, Python 3.10/3.11/3.12). No paid services, no live cloud calls.
