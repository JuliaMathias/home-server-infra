"""Deterministic tests for per-app backup retention boundaries."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retention import retention_candidates


class RetentionTest(unittest.TestCase):
    """Retention protects both recent time and minimum successful backup count."""

    def setUp(self):
        """Use a fixed UTC clock and app-scoped synthetic backup receipts."""
        self.now = datetime(2026, 10, 21, 22, tzinfo=timezone.utc)

    def receipt(self, index, hours, status="verified", app="notey"):
        """Build one synthetic receipt; no storage adapter is involved."""
        return {"id": str(index), "app": app, "status": status,
                "created_at": (self.now - timedelta(hours=hours)).isoformat()}

    def candidates(self, receipts, count=30, days=5, protected=()):
        """Apply Notey's explicit policy with an injected clock."""
        return retention_candidates(receipts, "notey", count, days, self.now, protected)

    def test_many_deployments_keep_all_recent_backups(self):
        """One hundred backups in five days are retained even above count 30."""
        self.assertEqual(self.candidates([self.receipt(i, i) for i in range(100)]), [])

    def test_sparse_backups_keep_thirty_regardless_of_age(self):
        """The newest thirty survive even when all are many months old."""
        self.assertEqual(self.candidates([self.receipt(i, 4000 + i) for i in range(30)]), [])

    def test_only_old_backups_beyond_count_expire(self):
        """Expiry requires age and count conditions simultaneously."""
        data = [self.receipt(i, 24*i) for i in range(40)]
        self.assertEqual(set(self.candidates(data)), {str(i) for i in range(30, 40)})

    def test_exact_five_day_boundary_is_retained(self):
        """Age equal to the minimum window does not qualify for deletion."""
        data = [self.receipt(i, i) for i in range(30)]
        data += [self.receipt("boundary", 120), self.receipt("old", 121)]
        self.assertEqual(self.candidates(data), ["old"])

    def test_failed_backups_do_not_displace_verified_points(self):
        """A failed new upload cannot push a valid backup outside minimum count."""
        data = [self.receipt(i, 200+i) for i in range(30)]
        data += [self.receipt("failed", 1, "failed"), self.receipt("partial", 2, "incomplete")]
        self.assertEqual(self.candidates(data), [])

    def test_incident_recovery_point_is_protected(self):
        """An unresolved migration incident can pin an otherwise expired backup."""
        data = [self.receipt(i, 200+i) for i in range(32)]
        self.assertEqual(self.candidates(data, protected=("31",)), ["30"])

    def test_other_app_policy_does_not_inherit_notey_values(self):
        """Each application must supply its own explicitly approved limits."""
        data = [self.receipt(i, 48*i, app="other-app") for i in range(6)]
        actual = retention_candidates(data, "other-app", 2, 1, self.now)
        self.assertEqual(set(actual), {"2", "3", "4", "5"})

    def test_invalid_metadata_prevents_a_deletion_plan(self):
        """Mixed apps, duplicate IDs, future dates and naive clocks fail closed."""
        cases = [
            [self.receipt(1, 200), self.receipt(1, 300)],
            [self.receipt(1, 200, app="other")],
            [self.receipt(1, -1)],
            [{"id": "1", "app": "notey", "status": "verified", "created_at": "2026-01-01"}],
        ]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.candidates(data)
        with self.assertRaises(ValueError):
            self.candidates([], count=0)


if __name__ == "__main__":
    unittest.main()
