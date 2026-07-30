"""Process-wide accidental-egress policy for Moira's pytest runtime.

This is cooperative CPython interception, not a security sandbox. It cannot
contain native/ctypes networking, immutable or cached pre-install raw socket
methods, SSL/native writes on pre-existing or foreign descriptors, startup
activity before repository conftest loading, or hostile child processes.
Only separately scoped runner-level egress denial can provide complete
containment; this Python policy does not.
"""

from __future__ import annotations

import _socket
from enum import Enum
import ipaddress
import os
import socket
import sys
from threading import RLock
from typing import Any


NETWORK_POLICY_ENVIRONMENT = "MOIRA_TEST_NETWORK_POLICY"
NETWORK_POLICY_DIAGNOSTIC = "Moira test network policy"


class NetworkMode(Enum):
    """Network capability admitted for the currently executing test item."""

    DENY = "deny"
    LOOPBACK = "loopback"
    EXTERNAL = "external"


class NetworkPolicyViolation(RuntimeError):
    """Raised before a forbidden CPython socket operation reaches the OS."""


_LOCK = RLock()
_ACTIVE_MODE = NetworkMode.DENY
_ACTIVE_NODEID = "<collection>"
_AUDIT_HOOK_INSTALLED = False
_AUDIT_CANARY_SEEN = False
_SOCKET_METHOD_GUARDS_INSTALLED = False
_ASYNCIO_METHOD_GUARDS_INSTALLED = False
_AUDIT_CANARY_EVENT = "moira.test_network_policy.audit_canary"
_RAW_SOCKET_TYPE = _socket.socket
_ORIGINAL_BIND = socket.socket.bind
_ORIGINAL_CONNECT = socket.socket.connect
_ORIGINAL_CONNECT_EX = socket.socket.connect_ex
_ORIGINAL_LISTEN = socket.socket.listen
_ORIGINAL_SEND = socket.socket.send
_ORIGINAL_SENDALL = socket.socket.sendall
_ORIGINAL_SENDFILE = getattr(socket.socket, "sendfile", None)
_ORIGINAL_SENDTO = socket.socket.sendto
_ORIGINAL_SENDMSG = getattr(socket.socket, "sendmsg", None)
_ADDRESS_EVENTS = {
    "socket.bind",
    "socket.connect",
    "socket.sendto",
    "socket.sendmsg",
}
_FORWARD_RESOLUTION_EVENTS = {
    "socket.getaddrinfo",
    "socket.gethostbyname",
    "socket.gethostbyname_ex",
}
_REVERSE_RESOLUTION_EVENTS = {
    "socket.gethostbyaddr",
    "socket.getnameinfo",
}


def _policy_snapshot() -> tuple[NetworkMode, str]:
    with _LOCK:
        return _ACTIVE_MODE, _ACTIVE_NODEID


def activate_network_mode(mode: NetworkMode, *, nodeid: str) -> None:
    """Activate one capability for the complete setup/call/teardown protocol."""

    if not isinstance(mode, NetworkMode):
        raise TypeError("mode must be a NetworkMode.")
    if not isinstance(nodeid, str) or not nodeid:
        raise ValueError("nodeid must be a nonblank string.")
    global _ACTIVE_MODE, _ACTIVE_NODEID
    with _LOCK:
        _ACTIVE_MODE = mode
        _ACTIVE_NODEID = nodeid
        os.environ[NETWORK_POLICY_ENVIRONMENT] = mode.value


def reset_network_mode(*, nodeid: str = "<between-tests>") -> None:
    """Restore deny mode after an item or interrupted protocol."""

    activate_network_mode(NetworkMode.DENY, nodeid=nodeid)


def _base_socket_kind(kind: object) -> int | None:
    try:
        value = int(kind)
    except (TypeError, ValueError):
        return None
    flags = int(getattr(socket, "SOCK_NONBLOCK", 0)) | int(
        getattr(socket, "SOCK_CLOEXEC", 0)
    )
    return value & ~flags


def _is_numeric_loopback(host: object) -> bool:
    if isinstance(host, bytes):
        try:
            host = host.decode("ascii")
        except UnicodeDecodeError:
            return False
    if not isinstance(host, str) or not host:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped.is_loopback
    return address.is_loopback


def _is_loopback_socket_address(sock: object, address: object) -> bool:
    family = getattr(sock, "family", None)
    unix_family = getattr(socket, "AF_UNIX", None)
    if unix_family is not None and family == unix_family:
        return isinstance(address, (str, bytes))
    if family not in {socket.AF_INET, socket.AF_INET6}:
        return False
    if not isinstance(address, tuple) or len(address) < 2:
        return False
    return _is_numeric_loopback(address[0])


def _violation(
    *,
    event: str,
    target: object,
    mode: NetworkMode,
    nodeid: str,
) -> NetworkPolicyViolation:
    if mode is NetworkMode.DENY:
        guidance = (
            "Unmarked tests have no destination-network capability; "
            "use @pytest.mark.loopback for numeric local endpoints and "
            "portable socket-pair or event-loop IPC."
        )
    else:
        guidance = (
            "Loopback tests admit only numeric 127.0.0.0/8, ::1, mapped IPv4 "
            "loopback, and AF_UNIX destinations."
        )
    return NetworkPolicyViolation(
        f"{NETWORK_POLICY_DIAGNOSTIC} mode={mode.value!r} denied {event} "
        f"target={target!r} for {nodeid}. {guidance}"
    )


def _guard_destination(
    sock: socket.socket,
    address: object,
    *,
    event: str,
) -> None:
    """Reject a forbidden address before CPython can resolve a hostname."""

    mode, nodeid = _policy_snapshot()
    if mode is NetworkMode.EXTERNAL:
        return
    if mode is NetworkMode.LOOPBACK and _is_loopback_socket_address(
        sock,
        address,
    ):
        return
    raise _violation(
        event=event,
        target=address,
        mode=mode,
        nodeid=nodeid,
    )


def _guard_connected_operation(
    sock: socket.socket,
    *,
    event: str,
) -> None:
    """Restrict writes on already-connected cooperative public sockets."""

    mode, nodeid = _policy_snapshot()
    if mode is NetworkMode.EXTERNAL:
        return
    try:
        peer: object = sock.getpeername()
    except OSError:
        peer = "<unconnected>"
    if mode is NetworkMode.LOOPBACK and _is_loopback_socket_address(sock, peer):
        return
    raise _violation(
        event=event,
        target=peer,
        mode=mode,
        nodeid=nodeid,
    )


def _guarded_bind(self: socket.socket, address: object) -> None:
    _guard_destination(self, address, event="socket.bind")
    return _ORIGINAL_BIND(self, address)


def _guarded_connect(self: socket.socket, address: object) -> None:
    _guard_destination(self, address, event="socket.connect")
    return _ORIGINAL_CONNECT(self, address)


def _guarded_connect_ex(self: socket.socket, address: object) -> int:
    _guard_destination(self, address, event="socket.connect")
    return _ORIGINAL_CONNECT_EX(self, address)


def _guarded_listen(
    self: socket.socket,
    *args: Any,
    **kwargs: Any,
) -> None:
    try:
        address: object = self.getsockname()
    except OSError:
        address = "<unbound>"
    _guard_destination(
        self,
        address,
        event="socket.listen",
    )
    return _ORIGINAL_LISTEN(self, *args, **kwargs)


def _guarded_send(self: socket.socket, *args: Any, **kwargs: Any) -> int:
    _guard_connected_operation(self, event="socket.send")
    return _ORIGINAL_SEND(self, *args, **kwargs)


def _guarded_sendall(
    self: socket.socket,
    *args: Any,
    **kwargs: Any,
) -> None:
    _guard_connected_operation(self, event="socket.sendall")
    return _ORIGINAL_SENDALL(self, *args, **kwargs)


def _guarded_sendfile(
    self: socket.socket,
    *args: Any,
    **kwargs: Any,
) -> object:
    _guard_connected_operation(self, event="socket.sendfile")
    if _ORIGINAL_SENDFILE is None:
        raise AttributeError("socket.sendfile is unavailable")
    return _ORIGINAL_SENDFILE(self, *args, **kwargs)


def _guarded_sendto(self: socket.socket, *args: Any, **kwargs: Any) -> int:
    address = kwargs.get("address")
    if address is None and len(args) >= 2:
        address = args[-1]
    _guard_destination(self, address, event="socket.sendto")
    return _ORIGINAL_SENDTO(self, *args, **kwargs)


def _guarded_sendmsg(self: socket.socket, *args: Any, **kwargs: Any) -> int:
    address = kwargs.get("address")
    if address is None and len(args) >= 4:
        address = args[3]
    if address is None:
        _guard_connected_operation(self, event="socket.sendmsg")
    else:
        _guard_destination(self, address, event="socket.sendmsg")
    if _ORIGINAL_SENDMSG is None:
        raise AttributeError("socket.sendmsg is unavailable")
    return _ORIGINAL_SENDMSG(self, *args, **kwargs)


def _install_socket_method_guards() -> None:
    """Guard Python socket addresses before the C layer can perform DNS."""

    global _SOCKET_METHOD_GUARDS_INSTALLED
    with _LOCK:
        if _SOCKET_METHOD_GUARDS_INSTALLED:
            return
        socket.socket.bind = _guarded_bind
        socket.socket.connect = _guarded_connect
        socket.socket.connect_ex = _guarded_connect_ex
        socket.socket.listen = _guarded_listen
        socket.socket.send = _guarded_send
        socket.socket.sendall = _guarded_sendall
        if _ORIGINAL_SENDFILE is not None:
            socket.socket.sendfile = _guarded_sendfile
        socket.socket.sendto = _guarded_sendto
        if _ORIGINAL_SENDMSG is not None:
            socket.socket.sendmsg = _guarded_sendmsg
        _SOCKET_METHOD_GUARDS_INSTALLED = True


def _install_asyncio_method_guards() -> None:
    """Guard asyncio operations that can bypass public socket methods."""

    global _ASYNCIO_METHOD_GUARDS_INSTALLED
    with _LOCK:
        if _ASYNCIO_METHOD_GUARDS_INSTALLED:
            return

        from asyncio.base_events import BaseEventLoop

        original_loop_sock_sendfile = getattr(
            BaseEventLoop,
            "sock_sendfile",
            None,
        )

        async def guarded_loop_sock_sendfile(
            self,
            sock,
            file,
            offset=0,
            count=None,
            *,
            fallback=True,
        ):
            if isinstance(sock, _RAW_SOCKET_TYPE):
                _guard_connected_operation(
                    sock,
                    event="asyncio.sock_sendfile",
                )
            if original_loop_sock_sendfile is None:
                raise AttributeError("asyncio sock_sendfile is unavailable")
            return await original_loop_sock_sendfile(
                self,
                sock,
                file,
                offset,
                count,
                fallback=fallback,
            )

        if original_loop_sock_sendfile is not None:
            BaseEventLoop.sock_sendfile = guarded_loop_sock_sendfile

        if sys.platform != "win32":
            _ASYNCIO_METHOD_GUARDS_INSTALLED = True
            return

        from asyncio.proactor_events import BaseProactorEventLoop
        from asyncio.windows_events import IocpProactor

        original_sock_connect = BaseProactorEventLoop.sock_connect
        original_sock_sendall = getattr(
            BaseProactorEventLoop,
            "sock_sendall",
            None,
        )
        original_sock_sendto = getattr(
            BaseProactorEventLoop,
            "sock_sendto",
            None,
        )
        original_iocp_connect = IocpProactor.connect
        original_iocp_send = getattr(IocpProactor, "send", None)
        original_iocp_sendfile = getattr(IocpProactor, "sendfile", None)
        original_iocp_sendto = getattr(IocpProactor, "sendto", None)

        async def guarded_sock_connect(self, sock, address):
            _guard_destination(
                sock,
                address,
                event="asyncio.proactor.sock_connect",
            )
            return await original_sock_connect(self, sock, address)

        async def guarded_sock_sendto(self, sock, data, address):
            _guard_destination(
                sock,
                address,
                event="asyncio.proactor.sock_sendto",
            )
            if original_sock_sendto is None:
                raise AttributeError("Proactor sock_sendto is unavailable")
            return await original_sock_sendto(self, sock, data, address)

        async def guarded_sock_sendall(self, sock, data):
            _guard_connected_operation(
                sock,
                event="asyncio.proactor.sock_sendall",
            )
            if original_sock_sendall is None:
                raise AttributeError("Proactor sock_sendall is unavailable")
            return await original_sock_sendall(self, sock, data)

        def guarded_iocp_connect(self, conn, address):
            _guard_destination(
                conn,
                address,
                event="asyncio.iocp.connect",
            )
            return original_iocp_connect(self, conn, address)

        def guarded_iocp_send(self, conn, buf, flags=0):
            if isinstance(conn, _RAW_SOCKET_TYPE):
                _guard_connected_operation(
                    conn,
                    event="asyncio.iocp.send",
                )
            if original_iocp_send is None:
                raise AttributeError("IOCP send is unavailable")
            return original_iocp_send(self, conn, buf, flags)

        def guarded_iocp_sendfile(self, sock, file, offset, count):
            if isinstance(sock, _RAW_SOCKET_TYPE):
                _guard_connected_operation(
                    sock,
                    event="asyncio.iocp.sendfile",
                )
            if original_iocp_sendfile is None:
                raise AttributeError("IOCP sendfile is unavailable")
            return original_iocp_sendfile(self, sock, file, offset, count)

        def guarded_iocp_sendto(self, conn, buf, flags=0, addr=None):
            if addr is not None:
                _guard_destination(
                    conn,
                    addr,
                    event="asyncio.iocp.sendto",
                )
            elif isinstance(conn, _RAW_SOCKET_TYPE):
                _guard_connected_operation(
                    conn,
                    event="asyncio.iocp.sendto",
                )
            if original_iocp_sendto is None:
                raise AttributeError("IOCP sendto is unavailable")
            return original_iocp_sendto(self, conn, buf, flags, addr)

        BaseProactorEventLoop.sock_connect = guarded_sock_connect
        if original_sock_sendall is not None:
            BaseProactorEventLoop.sock_sendall = guarded_sock_sendall
        if original_sock_sendto is not None:
            BaseProactorEventLoop.sock_sendto = guarded_sock_sendto
        IocpProactor.connect = guarded_iocp_connect
        if original_iocp_send is not None:
            IocpProactor.send = guarded_iocp_send
        if original_iocp_sendfile is not None:
            IocpProactor.sendfile = guarded_iocp_sendfile
        if original_iocp_sendto is not None:
            IocpProactor.sendto = guarded_iocp_sendto
        _ASYNCIO_METHOD_GUARDS_INSTALLED = True


def _audit_network_operation(event: str, args: tuple[Any, ...]) -> None:
    if event == _AUDIT_CANARY_EVENT:
        global _AUDIT_CANARY_SEEN
        with _LOCK:
            _AUDIT_CANARY_SEEN = True
        return

    mode, nodeid = _policy_snapshot()
    if mode is NetworkMode.EXTERNAL:
        return

    if event == "socket.__new__":
        sock = args[0] if args else None
        kind = args[2] if len(args) > 2 else None
        if (
            (
                isinstance(sock, _RAW_SOCKET_TYPE)
                and not isinstance(sock, socket.socket)
            )
            or _base_socket_kind(kind) == int(socket.SOCK_RAW)
        ):
            raise _violation(
                event=event,
                target=(
                    f"socket-type={type(sock).__module__}."
                    f"{type(sock).__qualname__}, kind={kind!r}"
                ),
                mode=mode,
                nodeid=nodeid,
            )
        return

    if event in _REVERSE_RESOLUTION_EVENTS:
        target = args[0] if args else "<missing>"
        raise _violation(
            event=event,
            target=target,
            mode=mode,
            nodeid=nodeid,
        )

    if event in _FORWARD_RESOLUTION_EVENTS:
        host = args[0] if args else None
        if mode is NetworkMode.LOOPBACK and _is_numeric_loopback(host):
            return
        raise _violation(
            event=event,
            target=host,
            mode=mode,
            nodeid=nodeid,
        )

    if event in _ADDRESS_EVENTS:
        sock = args[0] if args else None
        address = args[-1] if len(args) > 1 else None
        if event == "socket.sendmsg" and address is None:
            _guard_connected_operation(sock, event=event)
            return
        if mode is NetworkMode.LOOPBACK and _is_loopback_socket_address(
            sock,
            address,
        ):
            return
        raise _violation(
            event=event,
            target=address,
            mode=mode,
            nodeid=nodeid,
        )


def install_network_audit_hook() -> None:
    """Install process-wide address guards and the irreversible audit hook."""

    global _AUDIT_CANARY_SEEN, _AUDIT_HOOK_INSTALLED
    with _LOCK:
        if not _AUDIT_HOOK_INSTALLED:
            _AUDIT_CANARY_SEEN = False
            try:
                sys.addaudithook(_audit_network_operation)
                sys.audit(_AUDIT_CANARY_EVENT)
            except BaseException as exc:
                raise RuntimeError(
                    "Moira test network policy could not install its audit hook; "
                    "refusing to run with partial network interception."
                ) from exc
            if not _AUDIT_CANARY_SEEN:
                raise RuntimeError(
                    "Moira test network policy audit-hook installation was "
                    "suppressed; refusing to run with partial interception."
                )
            _AUDIT_HOOK_INSTALLED = True
        _install_socket_method_guards()
        _install_asyncio_method_guards()


def install_network_policy_from_environment() -> bool:
    """Install inherited policy in a cooperative Python child process."""

    raw_mode = os.environ.get(NETWORK_POLICY_ENVIRONMENT)
    if raw_mode is None:
        return False
    try:
        mode = NetworkMode(raw_mode)
    except ValueError:
        mode = NetworkMode.DENY
    activate_network_mode(mode, nodeid="<cooperative-python-child>")
    install_network_audit_hook()
    return True
