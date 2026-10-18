"""Minimal durable request-ownership and output-acceptance contract.

This fixture models control-plane semantics only.  It does not model an LLM,
KV-cache restoration, process crashes, filesystem durability, or network timing.
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass


class ContractError(RuntimeError):
    pass


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Lease:
    request_id: str
    generation: int


class Ledger:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions(
              request_id TEXT PRIMARY KEY,
              generation INTEGER NOT NULL,
              identity_digest TEXT NOT NULL,
              checkpoint_digest TEXT NOT NULL,
              produced_index INTEGER NOT NULL DEFAULT 0,
              acked_index INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS outputs(
              request_id TEXT NOT NULL,
              token_index INTEGER NOT NULL,
              token_digest TEXT NOT NULL,
              PRIMARY KEY(request_id, token_index)
            );
            CREATE TABLE IF NOT EXISTS client_accepts(
              request_id TEXT NOT NULL,
              token_index INTEGER NOT NULL,
              token_digest TEXT NOT NULL,
              PRIMARY KEY(request_id, token_index)
            );
            """
        )

    def close(self) -> None:
        self.db.close()

    def create(self, request_id: str, identity_digest: str, checkpoint_digest: str) -> None:
        self.db.execute(
            "INSERT INTO sessions VALUES (?, 0, ?, ?, 0, 0)",
            (request_id, identity_digest, checkpoint_digest),
        )

    def acquire(
        self,
        request_id: str,
        expected_generation: int,
        identity_digest: str,
        checkpoint_digest: str,
    ) -> Lease:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT generation, identity_digest, checkpoint_digest FROM sessions WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if row is None:
                raise ContractError("unknown_request")
            generation, stored_identity, stored_checkpoint = row
            if generation != expected_generation:
                raise ContractError("stale_expected_generation")
            if identity_digest != stored_identity:
                raise ContractError("incompatible_identity")
            if checkpoint_digest != stored_checkpoint:
                raise ContractError("incompatible_checkpoint")
            changed = self.db.execute(
                "UPDATE sessions SET generation=generation+1 WHERE request_id=? AND generation=?",
                (request_id, expected_generation),
            ).rowcount
            if changed != 1:
                raise ContractError("cas_lost")
            self.db.execute("COMMIT")
            return Lease(request_id, expected_generation + 1)
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def emit(self, lease: Lease, token_index: int, token: str) -> str:
        token_digest = digest(token)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT generation, produced_index FROM sessions WHERE request_id=?",
                (lease.request_id,),
            ).fetchone()
            if row is None:
                raise ContractError("unknown_request")
            generation, produced = row
            if generation != lease.generation:
                raise ContractError("stale_owner")
            existing = self.db.execute(
                "SELECT token_digest FROM outputs WHERE request_id=? AND token_index=?",
                (lease.request_id, token_index),
            ).fetchone()
            if existing is not None:
                if existing[0] != token_digest:
                    raise ContractError("conflicting_output")
                self.db.execute("COMMIT")
                return "server_duplicate"
            if token_index != produced + 1:
                raise ContractError("noncontiguous_output")
            self.db.execute(
                "INSERT INTO outputs VALUES (?, ?, ?)",
                (lease.request_id, token_index, token_digest),
            )
            self.db.execute(
                "UPDATE sessions SET produced_index=? WHERE request_id=?",
                (token_index, lease.request_id),
            )
            self.db.execute("COMMIT")
            return "persisted"
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def client_receive(self, request_id: str, token_index: int, token_digest: str) -> str:
        try:
            self.db.execute(
                "INSERT INTO client_accepts VALUES (?, ?, ?)",
                (request_id, token_index, token_digest),
            )
            return "accepted"
        except sqlite3.IntegrityError:
            existing = self.db.execute(
                "SELECT token_digest FROM client_accepts WHERE request_id=? AND token_index=?",
                (request_id, token_index),
            ).fetchone()[0]
            if existing != token_digest:
                raise ContractError("client_digest_conflict")
            return "deduplicated"

    def ack(self, lease: Lease, token_index: int) -> None:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT generation, produced_index, acked_index FROM sessions WHERE request_id=?",
                (lease.request_id,),
            ).fetchone()
            if row is None:
                raise ContractError("unknown_request")
            generation, produced, acked = row
            if generation != lease.generation:
                raise ContractError("stale_owner")
            if token_index < acked or token_index > produced:
                raise ContractError("invalid_ack")
            self.db.execute(
                "UPDATE sessions SET acked_index=? WHERE request_id=?",
                (token_index, lease.request_id),
            )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def pending(self, lease: Lease) -> list[tuple[int, str]]:
        row = self.db.execute(
            "SELECT generation, acked_index FROM sessions WHERE request_id=?",
            (lease.request_id,),
        ).fetchone()
        if row is None or row[0] != lease.generation:
            raise ContractError("stale_owner")
        return self.db.execute(
            "SELECT token_index, token_digest FROM outputs WHERE request_id=? AND token_index>? ORDER BY token_index",
            (lease.request_id, row[1]),
        ).fetchall()

    def state(self, request_id: str) -> dict:
        generation, produced, acked = self.db.execute(
            "SELECT generation, produced_index, acked_index FROM sessions WHERE request_id=?",
            (request_id,),
        ).fetchone()
        accepted = self.db.execute(
            "SELECT token_index, token_digest FROM client_accepts WHERE request_id=? ORDER BY token_index",
            (request_id,),
        ).fetchall()
        return {"generation": generation, "produced_index": produced,
                "acked_index": acked, "client_accepts": [list(row) for row in accepted]}
