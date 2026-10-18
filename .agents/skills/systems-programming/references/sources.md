# Sources and coverage

Book orientation: *Computer Systems: A Programmer’s Perspective*, 3rd edition (2016); Randal E. Bryant, David R. O’Hallaron.

**Coverage: partial. No full-book conversion.**

No authorized full edition available. Public author companion pages were accessible; guessed 3e sample URL returned 404 and preface/code-file requests were denied. Used public resource descriptions, POSIX and SEI CERT; no restricted instructor files acquired.

## Evidence map

| Source | Supports / locator |
| --- | --- |
| [Computer Systems: A Programmer's Perspective, 3rd Edition — authors](https://csapp.cs.cmu.edu/3e/home.html) | Edition and companion navigation only |
| [CS:APP3e source-code index](https://csapp.cs.cmu.edu/3e/code.html) | Topic orientation: data, memory, I/O, processes and concurrency; linked code not copied |
| [CS:APP3e laboratory descriptions](https://csapp.cs.cmu.edu/3e/labs.html) | Public descriptions only; no instructor materials/solutions acquired |
| [POSIX.1-2024 read](https://pubs.opengroup.org/onlinepubs/9799919799/functions/read.html) | Short reads, interruption, EOF, nonblocking errors |
| [POSIX.1-2024 write](https://pubs.opengroup.org/onlinepubs/9799919799/functions/write.html) | Short writes, EINTR, size limits, nonblocking errors and SIGPIPE |
| [SEI CERT C INT30-C](https://wiki.sei.cmu.edu/confluence/display/c/INT30-C.+Ensure+that+unsigned+integer+operations+do+not+wrap) | Unsigned wraparound and precondition checks for allocation arithmetic |

## Attribution boundaries

These procedures, scenarios, code, and decision tables are original engineering
synthesis. They are not quotations, reproductions of book examples, or a substitute
for the cited books. A contents page verifies scope/identity only. Supplemental
implementation documentation supports the stated mechanisms, not claims about
unread book chapters. Context-dependent choices are recommendations, not guarantees.

Read the mechanisms reference relevant to the task; do not load all references
automatically. Source snapshots were accessed on 2026-10-18. Original URLs, observed
HTTP status, hashes, extraction methods, and acquisition failures are recorded in
the repository’s `sources/manifest.json`. No source license transfers to this library.

## Not covered

- Full book, processor design, detailed assembly, linking and virtual memory; lab solutions
