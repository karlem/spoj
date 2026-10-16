# Model attempt log

`model-runs.jsonl` intentionally starts empty. It contains one JSON object per completed or stopped attempt, including unsuccessful attempts. No database or logger service is required. The manager records actual runs; never copy the illustrative record below into the log as evidence.

## V0 schema

All fields below are required except `usage` and `cost_usd`, which may be omitted or null when unknown. Use JSON null for unknown values rather than zero. UTC timestamps use ISO 8601; attempts are positive integers counted across implementation/fix retries for the same issue, even when models change.

| Field | Type / meaning |
| --- | --- |
| `schema_version` | Integer, currently `1` |
| `timestamp` | String, UTC time when the attempt ended/stopped |
| `issue_id` | String, `owner/repo#number` |
| `task_class` | String, e.g. mechanical, bounded-implementation, exploration, review, debugging |
| `harness` | String, actual CLI/harness used |
| `model` | String, actual provider/model identifier |
| `attempt` | Positive integer |
| `result` | `success`, `failure`, or `blocked` |
| `checks_passed` | Boolean, or null if not run/not applicable; true only if every required check passed |
| `checks` | Array of objects: `command` (string), `exit_code` (integer or null), `evidence` (path/URL string or null) |
| `reviewer_outcome` | `approved`, `changes_requested`, `not_run`, or `not_applicable` |
| `escalation` | Object: `occurred` (boolean), `to` and `reason` (strings or null) |
| `human_intervention` | Object: `occurred` (boolean), `reason` (string or null) |
| `usage` | Optional object with measured/estimated token counts or other provider units, plus `estimated` boolean; or null |
| `cost_usd` | Optional nonnegative number, approximate USD cost; or null |
| `commit` | String, evaluated commit SHA, or null if none exists |

Illustrative blocked attempt only; placeholders are not real IDs or results:

```json
{"schema_version":1,"timestamp":"2030-01-01T00:00:00Z","issue_id":"owner/repo#123","task_class":"bounded-implementation","harness":"opencode","model":"provider/model-id","attempt":1,"result":"blocked","checks_passed":null,"checks":[],"reviewer_outcome":"not_run","escalation":{"occurred":true,"to":"human","reason":"Acceptance criterion needs clarification"},"human_intervention":{"occurred":false,"reason":null},"usage":null,"cost_usd":null,"commit":null}
```

An attempt's success is not merge approval. Record failed checks and negative reviews accurately even if a later attempt succeeds. Model comparisons should account for task difficulty, review outcome, retries, and human help, not just completion or price.

Workers return records as handoff artifacts; the manager appends them serially in the integration checkout after writers there have stopped. Do not have concurrent workers append to one shared file. Preserve unsuccessful records when integrating branches and avoid duplicate entries. Commit records through the ordinary review workflow. Keep secrets, private prompts, and credentials out of this log.
