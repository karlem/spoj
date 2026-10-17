import multiprocessing

import pytest


@pytest.fixture(autouse=True)
def no_child_leak():
    before = {p.pid for p in multiprocessing.active_children()}
    yield
    after = {p.pid for p in multiprocessing.active_children()}
    assert after <= before, f"leaked child processes: {after-before}"
