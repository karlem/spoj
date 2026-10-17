# Canonical specifications

- [SPOI v0.1: local Qwen3 MoE experiment](spoi-v0.1.md) is authoritative for the local experiment.
- [Human authorization and scope](../engineering/local-experiment-approval.md) records the conversation evidence and its interpretation.

Use the specification installation commit as the approved revision in GitHub issue handoffs. The reviewed draft is retained for traceability and is not authoritative.

Future specification changes require human approval, installation in this index, and reassessment of affected issues. GitHub issues must reference the canonical revision and include bounded scope, acceptance criteria, validation, and resolved dependencies. Obtain human approval of every generated issue queue before execution. The local correctness/measurement stages were reviewed in this conversation and directly authorized by the instruction to start; preserve that scope in their issue handoffs. Missing specification means `BLOCKED`; no eligible issues means `IDLE: no eligible GitHub issues`. A spec/issue conflict requires human resolution.

- [Local TCP MoE correctness demonstration](local-tcp-parity.md) is an additive milestone authorized by the human on 2026-10-17. It preserves the original v0.1/native-Mac gates and #2 boundaries.
