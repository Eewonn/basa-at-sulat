"""Every engine test runs with a guard that refuses any connection that leaves this laptop (conftest.py)."""

import socket

import pytest

from netguard import NetworkBlocked


def test_a_connection_to_the_internet_is_refused():
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("93.184.216.34", 80), timeout=1)


def test_a_connection_to_a_name_that_is_not_local_is_refused():
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("example.com", 443), timeout=1)


def test_a_connection_on_this_laptop_still_works():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        with socket.create_connection(server.getsockname(), timeout=2):
            pass


def test_the_guard_cannot_be_swallowed_by_a_broad_except():
    try:
        try:
            socket.create_connection(("93.184.216.34", 80), timeout=1)
        except Exception:
            pytest.fail("a broad 'except Exception' in the code under test swallowed the block")
    except NetworkBlocked:
        pass
