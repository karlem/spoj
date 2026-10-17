# Local experiment authorization

Date: 2026-10-16. Source: this repository’s human conversation.

The human supplied `SPOI_V0_1_EXPERIMENT_AGENT.md`, confirmed "Exactly, this is what I’m saying: native Mac", reviewed the explanation of the small local MoE experiment and the proposed correctness/measurement work split, and directed: "Cool. Let’s start with something, dude."

This authorizes proceeding with the supplied tiny random-weight, CPU-only Qwen MoE experiment on the existing Mac, including recording its specification and tracking the two discussed implementation stages. Scope: correctness across two worker processes first, then the required diagnostics and run bundle. Code and correctness evidence are independently reviewed before scaling. The project objective is eventually combining device memory to run larger models.

This record interprets the instruction to start in the context of the reviewed scope; it does not claim a separate signature or approval of undisclosed work. No infrastructure purchase, model checkpoint download, remote experiment, push, or merge is authorized. The first implementation uses synthetic vectors; pretrained code-review generation is outside v0.1.
