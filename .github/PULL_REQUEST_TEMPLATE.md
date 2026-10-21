<!-- Fill in this template for the actual change.
Keep simple PRs short. Remove unused guidance and optional sections when filling it
in. Describe the final change, not the history of the conversation or every file. -->

## Summary

[Explain the problem and the resulting behavior in one or two sentences.]

## Changes

- [Main change and why it is needed.]
- [Other meaningful changes, including an important design choice or tradeoff.]

## Verification

<!-- Use Passed / Failed / Blocked / Not run. Give actual evidence, including the
revision/environment where relevant. Separate fake-service tests, real integration
and content-quality review. Link long manual procedures rather than copying them. -->

| Check | Result | Evidence |
| --- | --- | --- |
| Automated tests and build | [Result] | [Commands, test count, environment and relevant coverage] |
| CI on the latest PR head | [Result] | [Run link and commit] |
| Manual / integration checks | [Result] | [Actual steps/results, environment/devices, or linked procedure] |

<!-- Add screenshots or a short recording when a visual/interaction change needs
review. A screenshot or a successful build does not establish behavioral acceptance. -->

## Manual testing

**Needed:** [Yes / No — explain why. Passing automated tests alone is not a reason to skip relevant browser, device or integration checks.]

<!-- Keep the Needed statement in every PR. If No, remove the procedure below.
If Yes, include runnable instructions here. A longer maintained guide may be linked,
but identify its exact procedure and include enough context to start without chat
history. Separate instructions from evidence that the checks have actually run. -->

**Prerequisites:** [Required revision, environment/URL, services, device/browser, access and setup. Do not include credentials.]

**Test data:** [Exact synthetic fixture names and initial state; identify any separately authorized private-data checks.]

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | [Specific action or command] | [Observable result] |
| 2 | [Next action, including the relevant boundary/failure case] | [Observable result] |

**Pass/fail criteria:** [What must hold for the procedure to pass and what counts as failure.]

**Evidence to record:** [Revision, environment/device, actual outcome, screenshots/logs where useful; omit secrets and private content.]

**Cleanup:** [Remove only the named test artifacts or restore the initial state; preserve user data.]

**Execution:** [Passed / Failed / Blocked / Not run; who ran it, when, and any check still needed from the reviewer.]

## Deployment and recovery

**Rollout:** [Automatic after a passing user merge / manual exception / no runtime deployment.]

**Migrations and data:** [Schema/config changes, compatibility and effects on persisted data; write “None” when applicable.]

<!-- For a manual exception, explain why and provide a runnable plan or a link:
prerequisites, deployment order (including companion changes), exact commands,
readiness checks and failure handling. Never include credentials. -->

**Procedure:** [Deployment instructions or runbook link, if needed.]

**Recovery:** [How to recover if this change fails, including any migration limits; do not assume that reverting an image reverses a database change.]

## Remaining work

[Known limitations, failed/blocked/unrun acceptance checks, and the next action or
owner. State whether this is ready for code review, deployed or accepted. Write
“None” when there are no remaining items.]

## Related work

**Issue:** [Issue link. Use a closing keyword only if merging this PR should close it.]

**Dependencies / companion PRs:** [Links, ownership and required order, or “None”.]
