"""Adversarial contracts for deny/loopback/external test-network capability."""

from __future__ import annotations

import _socket
import io
import ipaddress
import os
from pathlib import Path
import socket
import subprocess
import sys
from textwrap import dedent
from typing import Callable

import pytest


_TESTS_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _TESTS_DIR.parent
_HARNESS_PATH = _TESTS_DIR / "conftest.py"
_NETWORK_POLICY_PATH = _TESTS_DIR / "support" / "network_policy.py"
_NETWORK_BOOTSTRAP_PATH = (
    _TESTS_DIR / "support" / "network_bootstrap" / "sitecustomize.py"
)
_TEST_NET_V4 = "198.51.100.1"
_TEST_NET_V6 = "2001:db8::1"
_POLICY_DIAGNOSTIC = "Moira test network policy"
_CACHED_SOCKET = socket.socket
_CACHED_CREATE_CONNECTION = socket.create_connection
_CACHED_GETADDRINFO = socket.getaddrinfo
_CACHED_RAW_SOCKET = _socket.socket
_POLICY_ENVIRONMENT = "MOIRA_TEST_NETWORK_POLICY"
_PYTEST_CONFIG = """\
[pytest]
addopts = -ra
markers =
    loopback: local IPC only; external destinations remain forbidden
    external_network: live external access; requires --run-external-network
    network: forbidden legacy marker retained only for an explicit migration error
    parallel: tests admitted for parallel execution
    property: property-based tests
"""
_NO_KERNEL_BOOTSTRAP = """

@pytest.fixture(scope="session", autouse=True)
def _bootstrap_kernel_singleton():
    \"\"\"Keep network-policy mini-projects independent of local kernels.\"\"\"
    yield
"""


def _policy_violation(operation: Callable[[], object]) -> None:
    with pytest.raises(RuntimeError, match=_POLICY_DIAGNOSTIC):
        operation()


def _make_policy_project(
    pytester: pytest.Pytester,
    source: str,
) -> None:
    mini_tests = pytester.path / "tests"
    mini_tests.mkdir()
    mini_support = mini_tests / "support"
    mini_support.mkdir()
    mini_support.joinpath("__init__.py").write_text("", encoding="utf-8")
    mini_support.joinpath("network_policy.py").write_text(
        _NETWORK_POLICY_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    mini_bootstrap = mini_support / "network_bootstrap"
    mini_bootstrap.mkdir()
    mini_bootstrap.joinpath("sitecustomize.py").write_text(
        _NETWORK_BOOTSTRAP_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    mini_tests.joinpath("conftest.py").write_text(
        _HARNESS_PATH.read_text(encoding="utf-8") + _NO_KERNEL_BOOTSTRAP,
        encoding="utf-8",
    )
    mini_tests.joinpath("KNOWN_ISSUES.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    mini_tests.joinpath("test_probe.py").write_text(
        dedent(source),
        encoding="utf-8",
    )
    pytester.path.joinpath("pytest.ini").write_text(
        _PYTEST_CONFIG,
        encoding="utf-8",
    )


def _run_policy_project(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    *arguments: str,
) -> pytest.RunResult:
    for name in (
        "MOIRA_TEST_MODE",
        "MOIRA_NO_DOWNLOAD",
        "MOIRA_STRICT_KNOWN_ISSUES",
        "MOIRA_SNAPSHOT_UPDATE",
        "MOIRA_GOLDEN_UPDATE",
        _POLICY_ENVIRONMENT,
    ):
        monkeypatch.delenv(name, raising=False)
    return pytester.runpytest_subprocess(
        "tests",
        *arguments,
        "--tb=short",
        timeout=45,
    )


def _combined_output(result: pytest.RunResult) -> str:
    return f"{result.stdout.str()}\n{result.stderr.str()}"


def test_unmarked_destination_operations_block_cached_and_raw_sockets() -> None:
    stream = _CACHED_SOCKET(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _policy_violation(lambda: stream.bind(("0.0.0.0", 0)))
        _policy_violation(stream.listen)
    finally:
        stream.close()

    _policy_violation(
        lambda: _CACHED_RAW_SOCKET(socket.AF_INET, socket.SOCK_STREAM)
    )


def test_raw_socket_subclass_cannot_bypass_pre_resolution_guards() -> None:
    class RawSocketSubclass(_CACHED_RAW_SOCKET):
        pass

    _policy_violation(
        lambda: RawSocketSubclass(socket.AF_INET, socket.SOCK_STREAM)
    )


@pytest.mark.parametrize(
    "operation",
    ("send", "sendall", "sendfile", "sendmsg"),
)
def test_preconnected_public_socket_cannot_write_after_deny_reset(
    operation: str,
) -> None:
    import support.network_policy as network_policy

    network_policy.activate_network_mode(
        network_policy.NetworkMode.LOOPBACK,
        nodeid="<preconnected-setup>",
    )
    left, right = socket.socketpair()
    network_policy.reset_network_mode(nodeid="<preconnected-deny>")
    try:
        def send_action() -> object:
            return left.send(b"x")

        def sendall_action() -> object:
            return left.sendall(b"x")

        def sendfile_action() -> object:
            return left.sendfile(io.BytesIO(b"x"))

        def sendmsg_action() -> object:
            return left.sendmsg([b"x"])

        if operation == "sendmsg" and not hasattr(left, "sendmsg"):
            pytest.skip("socket.sendmsg is unavailable")
        action = {
            "send": send_action,
            "sendall": sendall_action,
            "sendfile": sendfile_action,
            "sendmsg": sendmsg_action,
        }[operation]
        _policy_violation(action)
    finally:
        left.close()
        right.close()
        network_policy.reset_network_mode()


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows IOCP-specific connected-write guard",
)
@pytest.mark.parametrize("operation", ("send", "sendfile", "sendto"))
def test_preconnected_iocp_socket_cannot_write_after_deny_reset(
    operation: str,
) -> None:
    import asyncio

    import support.network_policy as network_policy

    network_policy.activate_network_mode(
        network_policy.NetworkMode.LOOPBACK,
        nodeid="<preconnected-iocp-setup>",
    )
    loop = asyncio.new_event_loop()
    left, right = socket.socketpair()
    left.setblocking(False)
    network_policy.reset_network_mode(nodeid="<preconnected-iocp-deny>")

    try:
        proactor = getattr(loop, "_proactor")
        action = {
            "send": lambda: proactor.send(left, b"x"),
            "sendfile": lambda: proactor.sendfile(
                left,
                io.BytesIO(b"x"),
                0,
                1,
            ),
            "sendto": lambda: proactor.sendto(left, b"x", 0, None),
        }[operation]
        _policy_violation(action)
    finally:
        network_policy.activate_network_mode(
            network_policy.NetworkMode.LOOPBACK,
            nodeid="<preconnected-iocp-cleanup>",
        )
        loop.close()
        left.close()
        right.close()
        network_policy.reset_network_mode()


def test_preconnected_asyncio_sendfile_cannot_write_after_deny_reset() -> None:
    import asyncio

    import support.network_policy as network_policy

    network_policy.activate_network_mode(
        network_policy.NetworkMode.LOOPBACK,
        nodeid="<preconnected-asyncio-sendfile-setup>",
    )
    loop = asyncio.new_event_loop()
    left, right = socket.socketpair()
    left.setblocking(False)
    network_policy.reset_network_mode(
        nodeid="<preconnected-asyncio-sendfile-deny>"
    )

    try:
        with pytest.raises(RuntimeError, match=_POLICY_DIAGNOSTIC):
            loop.run_until_complete(
                loop.sock_sendfile(left, io.BytesIO(b"x"))
            )
    finally:
        network_policy.activate_network_mode(
            network_policy.NetworkMode.LOOPBACK,
            nodeid="<preconnected-asyncio-sendfile-cleanup>",
        )
        loop.close()
        left.close()
        right.close()
        network_policy.reset_network_mode()


@pytest.mark.loopback
@pytest.mark.parametrize(
    "operation",
    (
        "bind",
        "connect",
        "connect_ex",
        "sendto",
        "sendmsg",
    ),
)
def test_direct_socket_hostname_is_rejected_before_resolution(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import support.network_policy as network_policy

    original_name = {
        "bind": "_ORIGINAL_BIND",
        "connect": "_ORIGINAL_CONNECT",
        "connect_ex": "_ORIGINAL_CONNECT_EX",
        "sendto": "_ORIGINAL_SENDTO",
        "sendmsg": "_ORIGINAL_SENDMSG",
    }[operation]
    guard_name = {
        "bind": "_guarded_bind",
        "connect": "_guarded_connect",
        "connect_ex": "_guarded_connect_ex",
        "sendto": "_guarded_sendto",
        "sendmsg": "_guarded_sendmsg",
    }[operation]
    public_method = getattr(socket.socket, operation, None)
    if public_method is None:
        pytest.skip(f"socket.{operation} is unavailable")
    assert public_method is getattr(network_policy, guard_name)

    reached_os_layer = False

    def fail_if_original_called(*args: object, **kwargs: object) -> object:
        del args, kwargs
        nonlocal reached_os_layer
        reached_os_layer = True
        raise AssertionError("socket operation reached the OS-facing method")

    monkeypatch.setattr(
        network_policy,
        original_name,
        fail_if_original_called,
    )
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as stream:
        def bind_action() -> object:
            return stream.bind(("localhost", 0))

        def connect_action() -> object:
            return stream.connect(("policy.invalid", 443))

        def connect_ex_action() -> object:
            return stream.connect_ex(("policy.invalid", 443))

        def sendto_action() -> object:
            return stream.sendto(b"x", ("policy.invalid", 443))

        def sendmsg_action() -> object:
            return stream.sendmsg(
                [b"x"],
                [],
                0,
                ("policy.invalid", 443),
            )

        if operation == "sendmsg" and not hasattr(stream, "sendmsg"):
            pytest.skip("socket.sendmsg is unavailable")
        action = {
            "bind": bind_action,
            "connect": connect_action,
            "connect_ex": connect_ex_action,
            "sendto": sendto_action,
            "sendmsg": sendmsg_action,
        }[operation]
        _policy_violation(action)
    assert not reached_os_layer


@pytest.mark.loopback
def test_loopback_ipv4_tcp_round_trip() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        with socket.create_connection(
            ("127.0.0.1", listener.getsockname()[1]),
            timeout=2,
        ) as client:
            connection, _address = listener.accept()
            with connection:
                client.sendall(b"moira")
                assert connection.recv(5) == b"moira"


@pytest.mark.loopback
def test_loopback_ipv6_tcp_round_trip() -> None:
    if not socket.has_ipv6:
        pytest.skip("IPv6 is unavailable")
    try:
        listener = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        listener.bind(("::1", 0))
        listener.listen(1)
    except OSError as exc:
        pytest.skip(f"IPv6 loopback is unavailable: {exc}")
    with listener:
        with socket.create_connection(
            ("::1", listener.getsockname()[1]),
            timeout=2,
        ) as client:
            connection, _address = listener.accept()
            with connection:
                client.sendall(b"urania")
                assert connection.recv(6) == b"urania"


@pytest.mark.loopback
def test_loopback_udp_round_trip() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(2)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(b"star", receiver.getsockname())
            payload, _address = receiver.recvfrom(16)
    assert payload == b"star"


@pytest.mark.loopback
def test_loopback_socketpair_remains_available() -> None:
    left, right = socket.socketpair()
    with left, right:
        left.sendall(b"ipc")
        assert right.recv(3) == b"ipc"


@pytest.mark.loopback
@pytest.mark.parametrize(
    ("label", "operation"),
    (
        (
            "create-connection-ipv4",
            lambda: socket.create_connection((_TEST_NET_V4, 443), timeout=0.01),
        ),
        (
            "cached-create-connection-ipv4",
            lambda: _CACHED_CREATE_CONNECTION((_TEST_NET_V4, 443), timeout=0.01),
        ),
        (
            "dns-hostname",
            lambda: socket.getaddrinfo("example.invalid", 443),
        ),
        (
            "cached-dns-hostname",
            lambda: _CACHED_GETADDRINFO("example.invalid", 443),
        ),
    ),
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_loopback_rejects_external_clients_and_dns(
    label: str,
    operation: Callable[[], object],
) -> None:
    del label
    _policy_violation(operation)


@pytest.mark.loopback
@pytest.mark.parametrize(
    ("family", "address"),
    (
        (socket.AF_INET, (_TEST_NET_V4, 443)),
        (socket.AF_INET, ("10.0.0.1", 443)),
        (socket.AF_INET, ("169.254.1.1", 443)),
        (socket.AF_INET, ("224.0.0.1", 443)),
        (socket.AF_INET6, (_TEST_NET_V6, 443)),
        (socket.AF_INET6, ("::ffff:198.51.100.1", 443)),
    ),
)
def test_loopback_rejects_non_loopback_connect_and_connect_ex(
    family: int,
    address: tuple[object, ...],
) -> None:
    for constructor in (socket.socket, _CACHED_SOCKET):
        stream = constructor(family, socket.SOCK_STREAM)
        try:
            _policy_violation(lambda: stream.connect(address))
            _policy_violation(lambda: stream.connect_ex(address))
        finally:
            stream.close()
    _policy_violation(
        lambda: _CACHED_RAW_SOCKET(family, socket.SOCK_STREAM)
    )


@pytest.mark.loopback
@pytest.mark.parametrize(
    ("family", "address"),
    (
        (socket.AF_INET, ("0.0.0.0", 0)),
        (socket.AF_INET, ("", 0)),
        (socket.AF_INET6, ("::", 0)),
    ),
)
def test_loopback_rejects_wildcard_binds(
    family: int,
    address: tuple[object, ...],
) -> None:
    with socket.socket(family, socket.SOCK_STREAM) as stream:
        _policy_violation(lambda: stream.bind(address))


@pytest.mark.loopback
def test_loopback_rejects_implicit_wildcard_listen() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        _policy_violation(stream.listen)


@pytest.mark.loopback
def test_loopback_rejects_external_udp_before_syscall() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as stream:
        _policy_violation(lambda: stream.sendto(b"blocked", (_TEST_NET_V4, 9)))


@pytest.mark.loopback
def test_numeric_loopback_resolution_is_admitted_without_hostname_dns() -> None:
    results = socket.getaddrinfo(
        "127.0.0.1",
        0,
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        flags=socket.AI_NUMERICHOST,
    )
    assert results
    assert all(
        ipaddress.ip_address(sockaddr[0]).is_loopback
        for _family, _kind, _protocol, _canonname, sockaddr in results
    )
    _policy_violation(lambda: socket.getaddrinfo("localhost", 80))
    _policy_violation(lambda: socket.gethostbyname("localhost"))
    _policy_violation(lambda: socket.gethostbyaddr("127.0.0.1"))
    _policy_violation(lambda: socket.getnameinfo(("127.0.0.1", 80), 0))


@pytest.mark.loopback
@pytest.mark.parametrize("client_name", ("urllib", "requests", "httpx"))
def test_common_python_http_clients_are_blocked_below_http(
    client_name: str,
) -> None:
    def no_cleanup() -> None:
        return None

    cleanup: Callable[[], object] = no_cleanup
    if client_name == "urllib":
        from urllib.request import build_opener, ProxyHandler

        def urllib_operation() -> object:
            return build_opener(ProxyHandler({})).open(
                f"http://{_TEST_NET_V4}:9/",
                timeout=0.01,
            )

        operation = urllib_operation
    elif client_name == "requests":
        requests = pytest.importorskip("requests")
        session = requests.Session()
        session.trust_env = False

        def requests_operation() -> object:
            return session.get(
                f"http://{_TEST_NET_V4}:9/",
                timeout=0.01,
            )

        operation = requests_operation
        cleanup = session.close
    else:
        httpx = pytest.importorskip("httpx")

        def httpx_operation() -> object:
            return httpx.get(
                f"http://{_TEST_NET_V4}:9/",
                timeout=0.01,
                trust_env=False,
            )

        operation = httpx_operation

    try:
        with pytest.raises(Exception) as caught:
            operation()
    finally:
        cleanup()
    diagnostic_chain = []
    current: BaseException | None = caught.value
    while current is not None and len(diagnostic_chain) < 12:
        diagnostic_chain.append(repr(current))
        current = current.__cause__ or current.__context__
    assert _POLICY_DIAGNOSTIC in "\n".join(diagnostic_chain)


@pytest.mark.loopback
def test_fastapi_testclient_retains_local_ipc() -> None:
    from fastapi.testclient import TestClient

    from moira_server.app import create_app
    from moira_server.config import ServerConfig

    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        assert client.get("/health").status_code == 200


@pytest.mark.loopback
def test_testclient_portal_thread_cannot_escape_loopback_policy() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/escape")
    def escape() -> dict[str, bool]:
        socket.getaddrinfo("example.invalid", 443)
        return {"escaped": True}

    with TestClient(app) as client:
        _policy_violation(lambda: client.get("/escape"))


@pytest.mark.loopback
@pytest.mark.parametrize("transport", ("tcp", "udp"))
def test_testclient_async_transport_cannot_bypass_windows_proactor_guard(
    transport: str,
) -> None:
    import asyncio

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/escape")
    async def escape() -> dict[str, bool]:
        if transport == "tcp":
            await asyncio.wait_for(
                asyncio.open_connection(_TEST_NET_V4, 443),
                timeout=0.1,
            )
        else:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as stream:
                stream.setblocking(False)
                loop = asyncio.get_running_loop()
                if hasattr(loop, "sock_sendto"):
                    await loop.sock_sendto(
                        stream,
                        b"x",
                        (_TEST_NET_V4, 9),
                    )
                elif hasattr(loop, "_proactor"):
                    proactor = loop._proactor
                    await proactor.sendto(
                        stream,
                        b"x",
                        0,
                        (_TEST_NET_V4, 9),
                    )
                else:
                    stream.sendto(b"x", (_TEST_NET_V4, 9))
        return {"escaped": True}

    with TestClient(app) as client:
        _policy_violation(lambda: client.get("/escape"))


def test_cooperative_python_child_inherits_deny_policy() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import socket; socket.socket().bind(('0.0.0.0', 0))",
        ],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert _POLICY_DIAGNOSTIC in f"{result.stdout}\n{result.stderr}"


def test_cooperative_python_child_inherits_policy_outside_repo(
    tmp_path: Path,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import socket; socket.socket().bind(('0.0.0.0', 0))",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert _POLICY_DIAGNOSTIC in f"{result.stdout}\n{result.stderr}"


@pytest.mark.loopback
def test_cooperative_python_child_inherits_loopback_only_policy() -> None:
    source = dedent(
        f"""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
            stream.bind(("127.0.0.1", 0))
        try:
            socket.create_connection(("{_TEST_NET_V4}", 443), timeout=0.01)
        except RuntimeError as exc:
            assert "{_POLICY_DIAGNOSTIC}" in str(exc)
        else:
            raise AssertionError("external destination escaped child policy")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_python_dash_s_documents_hostile_child_boundary() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            (
                "import socket,sys; socket.socket().close(); "
                "print('sitecustomize' in sys.modules)"
            ),
        ],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.stdout.strip() == "False"


def test_shadowing_sitecustomize_documents_cooperative_child_boundary(
    tmp_path: Path,
) -> None:
    tmp_path.joinpath("sitecustomize.py").write_text(
        "import os\nos.environ['MOIRA_SHADOW_SITE_LOADED'] = '1'\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["MOIRA_TEST_NETWORK_POLICY"] = "deny"
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(tmp_path),
            str(_NETWORK_BOOTSTRAP_PATH.parent),
        ]
    )
    source = dedent(
        """
        import os
        import socket

        assert os.environ["MOIRA_SHADOW_SITE_LOADED"] == "1"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
            stream.bind(("127.0.0.1", 0))
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_audit_hook_installation_fails_closed_when_vetoed() -> None:
    source = dedent(
        f"""
        import sys

        sys.path.insert(0, {str(_TESTS_DIR)!r})

        def veto_new_audit_hooks(event, args):
            del args
            if event == "sys.addaudithook":
                raise RuntimeError("veto")

        sys.addaudithook(veto_new_audit_hooks)

        from support.network_policy import install_network_audit_hook

        try:
            install_network_audit_hook()
        except RuntimeError as exc:
            assert "suppressed" in str(exc) or "could not install" in str(exc)
        else:
            raise AssertionError("suppressed audit hook was reported installed")
        """
    )
    result = subprocess.run(
        [sys.executable, "-S", "-c", source],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_cooperative_child_bootstrap_aborts_when_policy_install_is_vetoed(
    tmp_path: Path,
) -> None:
    driver = tmp_path / "sitecustomize.py"
    driver.write_text(
        dedent(
            f"""
            import runpy
            import sys

            def veto_new_audit_hooks(event, args):
                del args
                if event == "sys.addaudithook":
                    raise RuntimeError("veto")

            sys.addaudithook(veto_new_audit_hooks)
            runpy.run_path({str(_NETWORK_BOOTSTRAP_PATH)!r})
            """
        ),
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["MOIRA_TEST_NETWORK_POLICY"] = "deny"
    environment["PYTHONPATH"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, "-c", "raise AssertionError('startup continued')"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0, output
    assert "aborting Python startup" in output
    assert "startup continued" not in output


def test_cooperative_child_bootstrap_aborts_when_policy_import_fails(
    tmp_path: Path,
) -> None:
    fake_bootstrap = (
        tmp_path
        / "fake_tests"
        / "support"
        / "network_bootstrap"
        / "sitecustomize.py"
    )
    fake_bootstrap.parent.mkdir(parents=True)
    fake_bootstrap.write_text(
        _NETWORK_BOOTSTRAP_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    driver = tmp_path / "sitecustomize.py"
    driver.write_text(
        dedent(
            f"""
            import runpy

            runpy.run_path({str(fake_bootstrap)!r})
            """
        ),
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["MOIRA_TEST_NETWORK_POLICY"] = "deny"
    environment["PYTHONPATH"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, "-c", "raise AssertionError('startup continued')"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0, output
    assert "aborting Python startup" in output
    assert "startup continued" not in output


def test_cooperative_child_bootstrap_aborts_when_path_setup_fails(
    tmp_path: Path,
) -> None:
    driver = tmp_path / "sitecustomize.py"
    driver.write_text(
        dedent(
            f"""
            import pathlib
            import runpy

            def reject_resolution(self, *args, **kwargs):
                del self, args, kwargs
                raise OSError("path resolution veto")

            pathlib.Path.resolve = reject_resolution
            runpy.run_path({str(_NETWORK_BOOTSTRAP_PATH)!r})
            """
        ),
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["MOIRA_TEST_NETWORK_POLICY"] = "deny"
    environment["PYTHONPATH"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, "-c", "raise AssertionError('startup continued')"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0, output
    assert "aborting Python startup" in output
    assert "startup continued" not in output


def test_external_marker_without_option_is_explicitly_skipped(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_policy_project(
        pytester,
        """
        import pytest


        @pytest.mark.external_network
        def test_external_body_must_not_run_without_permission():
            raise AssertionError("external body executed without permission")
        """,
    )

    result = _run_policy_project(pytester, monkeypatch, "-q")

    result.assert_outcomes(skipped=1)
    output = _combined_output(result)
    assert "--run-external-network" in output
    assert "1 marked item(s) held in deny mode and skipped" in output


def test_external_deselection_is_not_reported_as_a_policy_skip(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_policy_project(
        pytester,
        """
        import pytest


        @pytest.mark.external_network
        def test_external_case():
            raise AssertionError("deselected external case executed")


        def test_unmarked_case():
            pass
        """,
    )

    result = _run_policy_project(
        pytester,
        monkeypatch,
        "-q",
        "-m",
        "not external_network",
    )

    result.assert_outcomes(passed=1, deselected=1)
    assert "held in deny mode and skipped" not in _combined_output(result)


def test_external_marker_and_option_are_both_required(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_policy_project(
        pytester,
        """
        import socket
        import pytest


        @pytest.mark.external_network
        def test_explicit_external_capability_allows_socket_operations():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
                stream.bind(("0.0.0.0", 0))
        """,
    )

    result = _run_policy_project(
        pytester,
        monkeypatch,
        "-q",
        "--run-external-network",
    )

    result.assert_outcomes(passed=1)


def test_external_option_is_admitted_only_in_external_only_process(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_policy_project(
        pytester,
        """
        import pytest


        @pytest.mark.external_network
        def test_explicit_external_case():
            pass


        def test_unmarked_case_is_not_selected():
            raise AssertionError("unmarked case entered external process")
        """,
    )

    result = _run_policy_project(
        pytester,
        monkeypatch,
        "-q",
        "--run-external-network",
        "-m",
        "external_network",
    )

    result.assert_outcomes(passed=1, deselected=1)


def test_external_option_alone_does_not_grant_unmarked_access(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_policy_project(
        pytester,
        f"""
        import socket
        import pytest


        def test_flag_alone_remains_denied():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
                with pytest.raises(RuntimeError, match={_POLICY_DIAGNOSTIC!r}):
                    stream.bind(("0.0.0.0", 0))
        """,
    )

    result = _run_policy_project(
        pytester,
        monkeypatch,
        "-q",
        "--run-external-network",
    )

    output = _combined_output(result)
    assert result.ret == pytest.ExitCode.USAGE_ERROR, output
    assert "external-only" in output


@pytest.mark.parametrize(
    ("marker_source", "diagnostic"),
    (
        ("pytestmark = pytest.mark.network", "legacy"),
        (
            "pytestmark = [pytest.mark.loopback, pytest.mark.external_network]",
            "conflicting",
        ),
    ),
)
def test_legacy_or_conflicting_markers_fail_collection(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    marker_source: str,
    diagnostic: str,
) -> None:
    _make_policy_project(
        pytester,
        f"""
        import pytest

        {marker_source}


        def test_marker_contract():
            pass
        """,
    )

    result = _run_policy_project(pytester, monkeypatch, "--collect-only", "-q")
    output = _combined_output(result)

    assert result.ret == pytest.ExitCode.USAGE_ERROR, output
    assert diagnostic in output.casefold()


@pytest.mark.parametrize(
    "marker_source",
    (
        "pytestmark = pytest.mark.network",
        "import pytest as pt\npytestmark = pt.mark.network",
        "from pytest import mark as pytest_mark\n"
        "pytestmark = pytest_mark.network",
    ),
)
def test_import_skipped_module_cannot_hide_legacy_network_marker(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    marker_source: str,
) -> None:
    indented_marker_source = marker_source.replace("\n", "\n        ")
    _make_policy_project(
        pytester,
        f"""
        import pytest

        pytest.importorskip("moira_dependency_that_does_not_exist")
        {indented_marker_source}


        def test_never_materialized():
            pass
        """,
    )

    result = _run_policy_project(pytester, monkeypatch, "--collect-only", "-q")
    output = _combined_output(result)

    assert result.ret == pytest.ExitCode.USAGE_ERROR, output
    assert "Legacy pytest.mark.network syntax is forbidden" in output


def test_legacy_marker_scan_fails_closed_on_ignored_malformed_module(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_policy_project(
        pytester,
        """
        def test_valid_module():
            pass
        """,
    )
    ignored_directory = pytester.path / "tests" / "legacy"
    ignored_directory.mkdir()
    ignored_directory.joinpath("test_hidden_marker.py").write_text(
        "import pytest\n"
        "pytestmark = pytest.mark.network\n"
        "def malformed(:\n",
        encoding="utf-8",
    )

    result = _run_policy_project(pytester, monkeypatch, "--collect-only", "-q")
    output = _combined_output(result)

    assert result.ret == pytest.ExitCode.USAGE_ERROR, output
    assert "refusing to continue with an incomplete migration check" in output
    assert "legacy/test_hidden_marker.py" in output


def test_policy_spans_fixture_setup_call_and_teardown(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_policy_project(
        pytester,
        """
        import socket
        import pytest


        def bind_loopback():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
                stream.bind(("127.0.0.1", 0))


        @pytest.fixture
        def loopback_fixture():
            bind_loopback()
            yield
            bind_loopback()


        @pytest.mark.loopback
        def test_all_three_phases_are_loopback(loopback_fixture):
            bind_loopback()
        """,
    )

    result = _run_policy_project(pytester, monkeypatch, "-q")

    result.assert_outcomes(passed=1)


def test_policy_resets_after_a_failing_item(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_policy_project(
        pytester,
        f"""
        import socket
        import pytest


        @pytest.mark.loopback
        def test_a_loopback_then_fails():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
                stream.bind(("127.0.0.1", 0))
            assert False, "intentional failure"


        def test_b_next_item_is_denied():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
                with pytest.raises(RuntimeError, match={_POLICY_DIAGNOSTIC!r}):
                    stream.bind(("0.0.0.0", 0))
        """,
    )

    result = _run_policy_project(pytester, monkeypatch, "-q")

    result.assert_outcomes(passed=1, failed=1)


def test_collection_time_destination_attempt_is_denied(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_policy_project(
        pytester,
        """
        import socket

        stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stream.bind(("0.0.0.0", 0))


        def test_never_collected():
            pass
        """,
    )

    result = _run_policy_project(pytester, monkeypatch, "--collect-only", "-q")
    output = _combined_output(result)

    assert result.ret == pytest.ExitCode.INTERRUPTED, output
    assert _POLICY_DIAGNOSTIC in output


def test_network_policy_is_worker_local_under_xdist(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("xdist")
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _make_policy_project(
        pytester,
        f"""
        from pathlib import Path
        import socket
        import pytest
        import support.network_policy as network_policy


        @pytest.mark.parametrize("index", range(4))
        def test_each_worker_defaults_to_deny(index):
            del index
            assert Path(network_policy.__file__).resolve().is_relative_to(
                Path.cwd()
            )
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
                with pytest.raises(RuntimeError, match={_POLICY_DIAGNOSTIC!r}):
                    stream.bind(("0.0.0.0", 0))
        """,
    )

    result = _run_policy_project(
        pytester,
        monkeypatch,
        "-q",
        "-p",
        "xdist.plugin",
        "-n",
        "2",
    )

    result.assert_outcomes(passed=4)
