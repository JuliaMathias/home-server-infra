"""Version 1 retention policy for explicitly configured Lara apps.

No networking, Docker operations, deletion or credentials live here. Adapters
must supply verified metadata; a policy decision is not a live acceptance result.
"""

from datetime import datetime, timedelta, timezone
import re


def retention_candidates(receipts, app, minimum_count, minimum_days, now, protected=()):
    """Return expired object IDs without deleting anything.

    Keep the newest count and every successful backup within the age window.
    Incomplete backups never replace verified recovery points and are not deleted
    by this policy. Reject mixed-app, ambiguous, future or malformed receipts.
    Incident-pinned backup IDs remain protected regardless of age/rank.
    """
    if (not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", app)
            or type(minimum_count) is not int or minimum_count < 1
            or type(minimum_days) is not int or minimum_days < 0
            or now.tzinfo is None):
        raise ValueError("Invalid explicit retention policy or clock")
    seen = set()
    completed = []
    for receipt in receipts:
        identifier = receipt["id"]
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError("Ambiguous backup identity")
        seen.add(identifier)
        if receipt["app"] != app:
            raise ValueError("Mixed application receipts")
        if receipt["status"] not in ("verified", "incomplete", "failed"):
            raise ValueError("Unknown backup state")
        created = datetime.fromisoformat(receipt["created_at"])
        if created.tzinfo is None or created > now:
            raise ValueError("Invalid or future backup timestamp")
        if receipt["status"] == "verified":
            completed.append((created.astimezone(timezone.utc), identifier))
    completed.sort(reverse=True)
    cutoff = now - timedelta(days=minimum_days)
    pinned = set(protected)
    return [identifier for created, identifier in completed[minimum_count:]
            if created < cutoff and identifier not in pinned]
