"""A test-time guard: refuse any connection that leaves this laptop.

Installed by the conftest.py of the engine and scripts suites. A test (or the code under test) that opens a
socket to anything but this machine raises NetworkBlocked. It derives from BaseException on purpose, so a
broad `except Exception` in the code under test can't swallow the block and let a test pass quietly.
"""

import ipaddress
import socket


class NetworkBlocked(BaseException):
    """Raised when something tries to connect somewhere other than this laptop."""


def is_local(address) -> bool:
    if isinstance(address, (str, bytes)):  # a unix socket path
        return True
    host = address[0]
    if isinstance(host, bytes):
        host = host.decode()
    if host in ("localhost", ""):
        return True
    try:
        ip = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False  # any other name would need a DNS lookup, which is the network
    return ip.is_loopback or ip.is_unspecified


_original = {}


def install() -> None:
    """Patch socket.socket.connect / connect_ex once. Safe to call again."""
    if _original:
        return
    for name in ("connect", "connect_ex"):
        original = getattr(socket.socket, name)
        _original[name] = original

        def guarded(self, address, _original=original):
            if not is_local(address):
                raise NetworkBlocked(f"blocked a connection to {address!r}: tests must stay on this laptop")
            return _original(self, address)

        setattr(socket.socket, name, guarded)


def uninstall() -> None:
    for name, original in _original.items():
        setattr(socket.socket, name, original)
    _original.clear()
