"""Deterministic release eligibility tests using synthetic API records."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release import eligible_release

class ReleaseTest(unittest.TestCase):
    """Only immutable releases tied to successful human-merged main CI qualify."""

    def setUp(self):
        """Prepare independently adjustable synthetic GitHub API records."""
        sha = "a"*40
        self.release = {"target_commitish": sha, "tag_name": "release-"+sha,
                        "resolved_tag_sha": sha, "immutable": True,
                        "draft": False, "prerelease": False}
        self.run = {"repository": {"full_name": "owner/app"}, "head_sha": sha,
                    "head_branch": "main", "path": ".github/workflows/ci.yml",
                    "event": "push", "status": "completed", "conclusion": "success"}
        self.prs = [{"merged_at": "2026-10-21T22:00:00Z", "merge_commit_sha": sha,
                     "base": {"ref": "main", "repo": {"full_name": "owner/app"}},
                     "merged_by": {"type": "User"}}]

    def eligible(self):
        """Call the production policy for the configured repository/workflow."""
        return eligible_release(self.release, self.run, self.prs,
                                "owner/app", ".github/workflows/ci.yml")

    def test_successful_exact_release_is_eligible(self):
        """A successful matching main revision merged by a user is accepted."""
        self.assertTrue(self.eligible())

    def test_failed_pending_cancelled_and_unverified_ci_are_rejected(self):
        """Only completed success is deployment evidence."""
        for status, conclusion in (("completed", "failure"), ("in_progress", None),
                                   ("completed", "cancelled"), ("completed", None)):
            with self.subTest(status=status, conclusion=conclusion):
                self.run.update(status=status, conclusion=conclusion)
                self.assertFalse(self.eligible())

    def test_wrong_revision_repository_branch_event_and_workflow_are_rejected(self):
        """A successful unrelated or PR-triggered workflow cannot qualify."""
        original = deepcopy(self.run)
        for key, value in (("head_sha", "b"*40), ("head_branch", "feature"),
                           ("event", "pull_request"), ("path", ".github/workflows/other.yml"),
                           ("repository", {"full_name": "other/app"})):
            self.run = deepcopy(original)
            self.run[key] = value
            with self.subTest(key=key):
                self.assertFalse(self.eligible())

    def test_mutable_draft_prerelease_or_mismatched_tag_are_rejected(self):
        """Published identity must be locked and resolve to the exact source."""
        original = deepcopy(self.release)
        for key, value in (("immutable", False), ("draft", True), ("prerelease", True),
                           ("resolved_tag_sha", "b"*40), ("target_commitish", "main"),
                           ("tag_name", "release-latest")):
            self.release = deepcopy(original)
            self.release[key] = value
            with self.subTest(key=key):
                self.assertFalse(self.eligible())

    def test_no_merge_unmerged_or_bot_merge_is_rejected(self):
        """A direct main push, unmerged PR or automated merge cannot qualify."""
        original = deepcopy(self.prs)
        self.prs = []
        self.assertFalse(self.eligible())
        for key, value in (("merged_at", None), ("merge_commit_sha", "b"*40),
                           ("merged_by", {"type": "Bot"})):
            self.prs = deepcopy(original)
            self.prs[0][key] = value
            with self.subTest(key=key):
                self.assertFalse(self.eligible())


if __name__ == "__main__":
    unittest.main()
