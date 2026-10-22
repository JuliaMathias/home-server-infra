"""Version 1 pure release eligibility policy; no network or execution. """

import re

def eligible_release(release, run, pull_requests, repository, workflow):
    """Require an immutable release of an exact successful human-merged revision.

    The release publisher must set target_commitish to a full source SHA and
    use release-<SHA>. The API adapter must resolve and verify the locked tag
    against the same SHA, independently of target_commitish. This function only
    evaluates metadata; the adapter must also hash downloaded assets/image data.
    """
    revision = release.get("target_commitish", "")
    if (not re.fullmatch(r"[0-9a-f]{40}", revision)
            or release.get("tag_name") != "release-" + revision
            or release.get("resolved_tag_sha") != revision
            or release.get("immutable") is not True
            or release.get("draft") is not False
            or release.get("prerelease") is not False):
        return False
    if (run.get("repository", {}).get("full_name") != repository
            or run.get("head_sha") != revision or run.get("head_branch") != "main"
            or run.get("path") != workflow or run.get("event") != "push"
            or run.get("status") != "completed" or run.get("conclusion") != "success"):
        return False
    return any(
        pr.get("merged_at") and pr.get("merge_commit_sha") == revision
        and pr.get("base", {}).get("ref") == "main"
        and pr.get("base", {}).get("repo", {}).get("full_name") == repository
        and pr.get("merged_by", {}).get("type") == "User"
        for pr in pull_requests
    )
