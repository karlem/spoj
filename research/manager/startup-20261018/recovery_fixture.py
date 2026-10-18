#!/usr/bin/env python3
"""Deterministic local transaction fixture; not distributed exactly-once."""
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

JOBS = [("job-a", 3), ("job-b", 7), ("job-c", 11)]
INPUT = {"jobs": JOBS, "delivery_plan": ["job-a:precommit-failure", "job-a:retry", "job-b:postcommit-lost-ack", "job-b:retry", "job-c:normal", "job-c:duplicate"]}


class InjectedFailure(Exception):
    pass


class Conflict(Exception):
    pass


def deliver(db, job_id, operand, result, fault=None):
    if result != operand * operand:
        raise ValueError("incorrect result")
    try:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute("SELECT operand, result FROM results WHERE job_id=?", (job_id,)).fetchone()
        if previous is not None:
            if previous != (operand, result):
                raise Conflict("same job id with conflicting input or result")
            db.commit()
            return "duplicate-suppressed"
        db.execute("INSERT INTO results VALUES (?, ?, ?)", (job_id, operand, result))
        if fault == "precommit":
            raise InjectedFailure("precommit failure")
        db.commit()
    except Exception:
        db.rollback()
        raise
    if fault == "lost-ack":
        raise InjectedFailure("postcommit acknowledgement lost")
    return "committed"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    events = []
    expected = [(job, n, n * n) for job, n in JOBS]
    with tempfile.TemporaryDirectory(prefix="spoj-startup-") as directory:
        path = Path(directory) / "jobs.sqlite"
        db = sqlite3.connect(path)
        db.execute("CREATE TABLE results (job_id TEXT PRIMARY KEY, operand INTEGER NOT NULL, result INTEGER NOT NULL)")
        db.commit()
        for job, n, fault in [("job-a", 3, "precommit"), ("job-a", 3, None), ("job-b", 7, "lost-ack"), ("job-b", 7, None), ("job-c", 11, None), ("job-c", 11, None)]:
            try:
                status = deliver(db, job, n, n * n, fault)
            except InjectedFailure as error:
                status = str(error)
            events.append({"job_id": job, "fault": fault, "status": status})
            if fault == "precommit":
                require(db.execute("SELECT COUNT(*) FROM results").fetchone()[0] == 0, "precommit insert survived rollback")
                db.close()
                db = sqlite3.connect(path)
            if fault == "lost-ack":
                require(db.execute("SELECT COUNT(*) FROM results WHERE job_id='job-b'").fetchone()[0] == 1, "lost ack lost committed result")
                db.close()
                db = sqlite3.connect(path)
        rejected = []
        for label, args, exception in [
            ("wrong-result-new-id", ("invalid", 5, 24), ValueError),
            ("wrong-result-existing-id", ("job-a", 3, 8), ValueError),
            ("conflicting-input-same-id", ("job-a", 4, 16), Conflict),
        ]:
            try:
                deliver(db, *args)
            except exception:
                rejected.append(label)
            else:
                raise AssertionError("negative case accepted: " + label)
        db.close()
        db = sqlite3.connect(path)
        rows = db.execute("SELECT job_id, operand, result FROM results ORDER BY job_id").fetchall()
        require(rows == expected, "reopened results differ from exactly one correct result per job")
        db.close()
        # Same successful deliveries as the protected path, including retries
        # after acknowledgement loss and duplicate delivery; precommit fault writes nothing.
        naive = sqlite3.connect(Path(directory) / "naive.sqlite")
        naive.execute("CREATE TABLE results (job_id TEXT, operand INTEGER, result INTEGER)")
        naive.commit()
        for job, n, fault in [("job-a", 3, "precommit"), ("job-a", 3, None), ("job-b", 7, "lost-ack"), ("job-b", 7, None), ("job-c", 11, None), ("job-c", 11, None)]:
            naive.execute("INSERT INTO results VALUES (?, ?, ?)", (job, n, n * n))
            if fault == "precommit":
                naive.rollback()
            else:
                naive.commit()
        naive.close()
        naive = sqlite3.connect(Path(directory) / "naive.sqlite")
        baseline = naive.execute("SELECT job_id, operand, result FROM results ORDER BY rowid").fetchall()
        naive.close()
        baseline_duplicates = len(baseline) - len({r[0] for r in baseline})
        require(baseline_duplicates == 2, "naive baseline did not expose duplicates")
        require(baseline != expected, "naive baseline unexpectedly passes invariant")
        print(json.dumps({
            "status": "PASS", "input": INPUT,
            "input_sha256": hashlib.sha256(json.dumps(INPUT, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "events": events, "negative_checks_rejected": rejected,
            "reopened_rows": rows, "naive_rows": baseline,
            "naive_duplicate_count": baseline_duplicates,
            "claims": "Local SQLite atomic transaction and unique-ID duplicate suppression only; injected exceptions and database reopen, no process kill, network or distributed exactly-once claim."
        }, sort_keys=True))


if __name__ == "__main__":
    main()
