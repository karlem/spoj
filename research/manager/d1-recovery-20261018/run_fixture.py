from __future__ import annotations

import json
import os
import platform
import tempfile

from recovery_contract import ContractError, Ledger, digest


def expect_error(events: list[dict], name: str, fn) -> None:
    try:
        fn()
    except ContractError as exc:
        events.append({"event": name, "rejected": str(exc)})
    else:
        raise AssertionError(f"{name} was not rejected")


def run() -> dict:
    identity = digest("model=m|tokenizer=t|backend=b|abi=1")
    checkpoint = digest("checkpoint-0")
    request_id = "request-001"
    tokens = {1: "alpha", 2: "beta", 3: "gamma"}
    events: list[dict] = []
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "ledger.sqlite")
        ledger = Ledger(path)
        ledger.create(request_id, identity, checkpoint)
        first = ledger.acquire(request_id, 0, identity, checkpoint)

        ledger.emit(first, 1, tokens[1])
        events.append({"event": "receive_1", "result": ledger.client_receive(request_id, 1, digest(tokens[1]))})
        ledger.ack(first, 1)
        ledger.emit(first, 2, tokens[2])
        events.append({"event": "receive_2_ack_lost", "result": ledger.client_receive(request_id, 2, digest(tokens[2]))})

        second = ledger.acquire(request_id, 1, identity, checkpoint)
        expect_error(events, "stale_expected_generation", lambda: ledger.acquire(request_id, 1, identity, checkpoint))
        expect_error(events, "stale_owner", lambda: ledger.emit(first, 3, "stale"))
        expect_error(events, "incompatible_identity", lambda: ledger.acquire(request_id, 2, digest("wrong"), checkpoint))
        expect_error(events, "incompatible_checkpoint", lambda: ledger.acquire(request_id, 2, identity, digest("wrong")))

        pending = ledger.pending(second)
        assert pending == [(2, digest(tokens[2]))]
        events.append({"event": "redeliver_2", "result": ledger.client_receive(request_id, *pending[0])})
        ledger.ack(second, 2)
        ledger.emit(second, 3, tokens[3])
        events.append({"event": "receive_3", "result": ledger.client_receive(request_id, 3, digest(tokens[3]))})
        ledger.ack(second, 3)
        expect_error(events, "conflicting_output", lambda: ledger.emit(second, 3, "different"))
        expect_error(events, "client_digest_conflict", lambda: ledger.client_receive(request_id, 3, digest("different")))

        state = ledger.state(request_id)
        ledger.close()

    expected = [[i, digest(tokens[i])] for i in (1, 2, 3)]
    assert state == {"generation": 2, "produced_index": 3, "acked_index": 3, "client_accepts": expected}
    assert [e.get("result") for e in events if "result" in e] == ["accepted", "accepted", "deduplicated", "accepted"]
    rejected = {e["event"] for e in events if "rejected" in e}
    assert rejected == {"stale_expected_generation", "stale_owner", "incompatible_identity", "incompatible_checkpoint", "conflicting_output", "client_digest_conflict"}

    naive = [1, 2, 2, 3]
    return {
        "fixture": "epoch-fenced-output-contract-v1",
        "scope": "control-plane simulation; no model, KV restore, process kill, power-loss or network measurement",
        "input_hashes": {"identity": identity, "checkpoint": checkpoint,
                         "tokens": digest(json.dumps(tokens, sort_keys=True))},
        "events": events,
        "final_state": state,
        "naive_append_indices": naive,
        "naive_duplicate_count": len(naive) - len(set(naive)),
        "checks": {"client_accepts_exactly_once": True, "acked_monotonic_to_3": True,
                   "stale_and_conflicting_rejected": True, "lost_ack_redelivery_deduplicated": True},
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
