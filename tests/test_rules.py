import unittest
from datetime import date, timedelta

from fss_audit.model import FileSystem, Snap, parse_date, ExportError
from fss_audit.rules import (
    exit_code,
    rule_mature_without_snapshots,
    rule_prod_without_snapshots,
    rule_stale_recovery_point,
    rule_unowned,
    run_all,
)

AS_OF = date(2026, 11, 18)


def fs(days_old=10, prod=False, owner="team", snaps=()):
    return FileSystem(
        ocid="ocid1.filesystem.oc1..x",
        display_name="fs",
        created_at=AS_OF - timedelta(days=days_old),
        tags=({"tier": "prod"} if prod else {"tier": "dev"}) | ({"owner": owner} if owner is not None else {}),
        snapshots=tuple(snaps),
    )


def snap(days_old=1, name="s"):
    return Snap(name=name, created_at=AS_OF - timedelta(days=days_old))


class TestFss001(unittest.TestCase):
    def test_fires_prod_zero_snapshots(self):
        out = rule_prod_without_snapshots((fs(prod=True),), AS_OF)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "HIGH")

    def test_quiet_dev_zero_snapshots(self):
        self.assertEqual(rule_prod_without_snapshots((fs(prod=False),), AS_OF), [])

    def test_quiet_prod_with_snapshot(self):
        self.assertEqual(rule_prod_without_snapshots((fs(prod=True, snaps=[snap()]),), AS_OF), [])


class TestFss002(unittest.TestCase):
    def test_fires_stale(self):
        out = rule_stale_recovery_point((fs(snaps=[snap(days_old=30)]),), AS_OF)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "MEDIUM")

    def test_boundary_7_days_quiet(self):
        self.assertEqual(rule_stale_recovery_point((fs(snaps=[snap(days_old=7)]),), AS_OF), [])

    def test_no_snapshots_not_stale(self):
        self.assertEqual(rule_stale_recovery_point((fs(),), AS_OF), [])


class TestFss003(unittest.TestCase):
    def test_fires_mature_zero_snapshots(self):
        out = rule_mature_without_snapshots((fs(days_old=45),), AS_OF)
        self.assertEqual(len(out), 1)

    def test_boundary_30_quiet(self):
        self.assertEqual(rule_mature_without_snapshots((fs(days_old=30),), AS_OF), [])

    def test_mature_with_snapshot_quiet(self):
        self.assertEqual(rule_mature_without_snapshots((fs(days_old=90, snaps=[snap()]),), AS_OF), [])


class TestFss004(unittest.TestCase):
    def test_fires_no_owner(self):
        self.assertEqual(len(rule_unowned((fs(owner=None),), AS_OF)), 1)

    def test_blank_owner_counts(self):
        self.assertEqual(len(rule_unowned((fs(owner=" "),), AS_OF)), 1)


class TestAggregation(unittest.TestCase):
    def test_exit_2_on_high(self):
        self.assertEqual(exit_code(run_all((fs(prod=True),), AS_OF)), 2)

    def test_exit_1_medium_only(self):
        self.assertEqual(exit_code(run_all((fs(days_old=45, owner="t"),), AS_OF)), 1)

    def test_exit_0_clean(self):
        self.assertEqual(exit_code(run_all((fs(snaps=[snap()]),), AS_OF)), 0)

    def test_sorted_high_first(self):
        findings = run_all((fs(prod=True, days_old=45, owner=None),), AS_OF)
        self.assertEqual(findings[0].severity, "HIGH")
        self.assertEqual(findings[-1].severity, "LOW")


class TestParsing(unittest.TestCase):
    def test_parse_date_ok(self):
        self.assertEqual(parse_date("2026-02-03", "t"), date(2026, 2, 3))

    def test_parse_date_bad(self):
        with self.assertRaises(ExportError):
            parse_date("yesterday", "t")


if __name__ == "__main__":
    unittest.main()
