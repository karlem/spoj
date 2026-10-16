# Factory workflow V0

This is an operating policy, not an autonomous manager implementation. The approved local experiment is indexed in `docs/specs/README.md`; follow the issue gate below. Work beyond that experiment requires human-approved requirements.

## Roles and routing

| Role | Responsibility |
| --- | --- |
| Manager | Read the canonical spec; inspect GitHub Issues and dependencies; choose eligible work; classify difficulty, uncertainty, and blast radius; select worker/model; create the worktree; delegate; monitor status; invoke checks; request independent review; route findings to a fixer; escalate; assemble a merge-ready result. Stay idle when no eligible issues exist. |
| Cheap worker | Use OpenCode Go models for bounded implementation, mechanical refactors within scope, boilerplate, straightforward tests, docs, read-only exploration, and clearly specified bug fixes. |
| Frontier worker | Use Codex/OpenAI for architecture, ambiguity, difficult debugging, concurrency/networking/systems problems, cross-cutting or high-blast-radius changes, and repeated worker failure. Difficult spec analysis and high-risk final review may use the strongest frontier model. |
| Reviewer | Independently inspect issue/spec compliance, correctness, missing tests, regressions, edge cases, error handling, concurrency/resource lifecycle, architectural violations, and benchmark validity where relevant. Report findings with locations and evidence; do not automatically edit code. |
| Fixer | Receive the original issue, implementation revision, failed checks, and review findings. Take exclusive ownership of the task worktree after the implementer stops, make targeted corrections, and return evidence for rechecking and review. |

Provisional routing, with no custom router:

| Task | Selection |
| --- | --- |
| Low-risk mechanical work | Cheapest proven capable model |
| Bounded implementation | Stronger cheap model |
| Exploration | Cheap read-only agent |
| Review | Independent medium/strong model |
| Architecture, ambiguity, difficult debugging | Codex/frontier model |
| Two failed worker attempts on one issue | Stop retries; manager escalates to frontier or human |
| High blast radius | Strong review required |

Record the concrete model ID and harness actually used. Choose available OpenCode Go models through the installed CLI; do not assume aliases, prices, or capabilities. Until evidence exists, describe selections as provisional. Use the [model log](../../.factory/README.md) to later compare success, review quality, retries, human intervention, and cost for comparable task classes.

## Issue to merge-ready

1. **Gate:** verify the human-approved canonical spec and issue queue. An eligible issue is open, unowned, references the approved spec revision, has bounded scope and testable acceptance criteria, and has resolved dependencies. A dependency is resolved when its required artifacts are merged/available and verified, not just because another worker claims completion. Missing spec means `BLOCKED`; no eligible issues means `IDLE`. Inaccessible GitHub or ambiguous requirements mean `BLOCKED`, not an empty queue.
2. **Assign:** manager records difficulty, uncertainty, blast radius, selected harness/model, issue owner, branch, worktree path, base commit, spec revision, and attempt number. One manager assigns ownership; parallel managers must not independently claim the same issue. Give the worker the full issue, spec references, validation commands, and constraints.
3. **Implement:** the sole writer works within the issue. Report status and evidence at meaningful milestones. Record unexpected ambiguity or failure and stop safely for escalation when necessary.
4. **Check:** run `scripts/check.sh` and issue-specific validation. Record commands, exit codes, environment prerequisites, and useful output. Failures or missing validation block progress. The Phase 0 no-op is never evidence that acceptance criteria passed.
5. **Review:** freeze an implementation commit and request an independent reviewer. Provide the issue, spec revision, diff/base commit, check evidence, and artifacts. Reviewer reports findings and disposition; if independence is unavailable, disclose that limitation for human decision. High-blast-radius work still requires strong review.
6. **Fix:** hand ownership to a fixer with the issue, implementation, failed checks, and findings. Re-run checks after fixes and have the reviewer verify resolutions against the new commit. Count failed implementation/fix attempts toward the two-attempt escalation threshold. Do not drop unresolved findings silently.
7. **Finalize:** run final checks on the reviewed commit. If the base or implementation changes, revalidate and repeat affected review. Present issue/spec links, base/head commits, acceptance-criteria evidence, check results, review identity/outcome, resolved findings, limitations, and expected artifacts. Manager reports `DONE` only when merge-ready; the human decides whether to merge.

## Worktree ownership

Keep the main checkout as the integration/cockpit location. Each implementation task gets one GitHub issue, one branch, one worktree, and one owning implementation agent. Concurrent writers never share a working tree. A reviewer may read the frozen task tree; a reviewer needing writable test artifacts uses a separate detached worktree. Pause implementation while the reviewer inspects the frozen commit.

Future example only, after issue 12 exists and is eligible; substitute its actual ID:

```sh
# From the main checkout, with a clean working tree:
git fetch origin
git worktree list
mkdir -p ../spoj-worktrees
git worktree add -b issue-12 ../spoj-worktrees/issue-12 origin/main
cd ../spoj-worktrees/issue-12
# Start the assigned agent here, with its issue/spec handoff.
./scripts/check.sh
```

Other workers use `../spoj-worktrees/issue-13`, etc. Check branch/worktree ownership before reuse; never reset another agent's work. Serialize commits and integration in the main checkout. Worktree removal, discarding work, or branch deletion needs explicit authority; verify saved commits and a clean worktree first.

## CLI, cockpit, and persistence

- **GitHub:** use `gh issue list --state open` and `gh issue view <number>` when authenticated, or the GitHub interface. Create only issues within the approved experiment and authorized work queue.
- **Codex:** from the assigned worktree, run `codex` for a frontier session. Pass the issue/spec handoff and require reading `AGENTS.md`; choose an available model deliberately. `codex --help` describes interactive and noninteractive (`exec`) operation for the installed version.
- **OpenCode:** from the assigned worktree, run `opencode`, select an available OpenCode Go model, and give it the same handoff and rules. `opencode --help` and `opencode models --help` describe the installed interface. For read-only exploration/review, configure read-only permissions in the harness; a role name alone is not an access control.
- **cmux:** suggested workspace `SPOJ`, with manager, worker, reviewer, and shell/tests/logs panes. cmux is the human cockpit only. Every handoff must include ordinary paths and git revisions; pane identity is not task ownership or durable state.
- **Herdr:** intended to host persistent sessions such as manager, worker-1, worker-2, and reviewer while the human detaches. When eligible work exists, use the installed Herdr interface to start the selected CLI in its assigned worktree with the recorded handoff. Consult `herdr --help` for version-specific setup. Verify detach/reconnect behavior before relying on persistence; a terminal pane alone does not ensure it.

Nothing in the repository requires cmux or Herdr for correctness. Later persistent operation should use a supported persistent session or noninteractive CLI mode, with durable status and output, so a permanent interactive terminal is unnecessary. Do not disable approvals to make unattended execution continue; an action needing human input becomes `BLOCKED` until answered.

## Status and safe stopping

| State | Meaning |
| --- | --- |
| WORKING | An eligible issue has an owning agent actively executing it. |
| IDLE | `IDLE: no eligible GitHub issues`; wait for an explicit queue change. |
| BLOCKED | A required spec, dependency, access, clarification, or human decision is missing; include the reason and unblock condition. |
| REVIEW | A fixed commit is awaiting or undergoing review. |
| FAILED | An attempt or check failed; preserve evidence and route to fixer/escalation. |
| DONE | Evidence supports a reviewed, merge-ready result; merge still requires human authority. |

For future sessions, write status at start, transitions, and before detach/exit: UTC timestamp, state, issue, role/model, branch/worktree, commit, attempt, last check outcome, blocker/next action, and evidence locations. Keep a Markdown handoff and command logs at recorded durable local paths outside tracked source; mirror actionable outcomes to the assigned issue when authorized. Do not leave essential status only in scrollback or agent memory. Keep credentials out of logs.

On restart, read the handoff and recheck git state, ownership, issue eligibility, and spec revision before resuming. Detach may leave a supported persistent process running; blocking must stop further writes safely. Never busy-loop, invent work, bypass failed checks, or fabricate completion. No scheduler, database, message queue, custom dashboard, or orchestration framework is needed for V0; add infrastructure only for an observed bottleneck with human approval.
