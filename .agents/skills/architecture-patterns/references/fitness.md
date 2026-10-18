# Make decisions observable

A fitness check provides evidence that a chosen characteristic is maintained.
It can be an automated dependency test, load check, security check, or human review
with explicit criteria. Select checks from the decision, not from whatever a tool
can measure easily.

## Original dependency constraint

Decision: checkout domain policy must not depend directly on a vendor payment SDK.
An application adapter owns the integration. A check can reject an import edge
from `checkout.domain` to `vendor.payment`, while allowing the adapter to depend
on both. Enumerate packages/modules accurately, including generated code and
reflection/plugin paths that static inspection may miss.

A toy graph fixture is useful for validating the intended rule, but a production
check must actually inspect the repository's dependency representation. The local
evaluation tests only the rule semantics and explicitly does not claim to scan
a Java/TypeScript codebase. ArchUnit is one primary example for Java architecture
rules; use a suitable tool for the target language.

## Scope checks to properties

| Decision | Check | Blind spot |
| --- | --- | --- |
| Stable consumer contract | Test old/new schemas and compatibility rules | Doesn't guarantee semantic equivalence |
| Dependency direction | Inspect actual module import/dependency graph | Dynamic dependencies may be missed |
| Finite recovery time | Restore drill with realistic size | One drill doesn't cover every outage |
| Tenant containment | Overload one tenant while measuring another | Test load may miss production skew |
| Bounded critical path | End-to-end latency test with dependency failure | Synthetic environment may differ |

## CI and operational cadence

Run cheap static checks per change. Run expensive production-like load/restore
exercises on a defined cadence and before risky changes. Record thresholds,
owners, fixtures, and procedures for justified exceptions. Quarantining a flaky
check without an owner can silently remove a safeguard.

Review failures as evidence of either an implementation regression or an outdated
decision. Do not change the threshold simply to make CI pass. If the architectural
constraint no longer fits, update the ADR and show the measured trade-off.

Exercise: a dependency test passes, but checkout fails whenever recommendations
fail. Explain why the static dependency property did not establish runtime fault
isolation, and add a targeted failure-injection check with a user-facing outcome.
