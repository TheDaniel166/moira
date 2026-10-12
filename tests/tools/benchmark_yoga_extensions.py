"""Reproducible VED-012 cost receipt; observed timings, not acceptance thresholds.

Run from repository root with MOIRA_NO_DOWNLOAD=1 and the project runtime.
Every HTTP result is compared with the complete canonical engine proof.
"""

from argparse import ArgumentParser
import hashlib
import json
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from moira import evaluate_yoga_extensions, list_yoga_extension_rules  # noqa: E402
from moira_server.app import create_app  # noqa: E402
from moira_server.config import ServerConfig  # noqa: E402
from moira_server.services.yoga_extensions import serialize_yoga_extensions  # noqa: E402


def timing(function):
    start = perf_counter()
    value = function()
    return value, (perf_counter() - start) * 1000


def summary(values):
    ordered = sorted(values)
    return {
        "n": len(values),
        "median_ms": median(values),
        "p95_ms": ordered[int(0.95 * (len(values) - 1))],
        "max_ms": max(values),
    }


def main():
    parser = ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / "tests/fixtures/yoga_extensions/source_cases.json"
    cases = json.loads(source.read_text())["cases"]
    profiles = [p.profile_id for p in list_yoga_extension_rules().profiles]
    requests = [
        dict(
            sidereal_longitudes=c["longitudes"],
            lagna_sidereal_lon=c["lagna"],
            profile_ids=profiles,
        )
        for c in cases
    ]
    first, cold_engine = timing(lambda: evaluate_yoga_extensions(**requests[0]))
    assert first.evaluated_count == 21
    expected = [
        serialize_yoga_extensions(evaluate_yoga_extensions(**r)).model_dump(mode="json")
        for r in requests
    ]
    engine_times = []
    for _ in range(3):
        for request, want in zip(requests, expected):
            result, elapsed = timing(lambda: evaluate_yoga_extensions(**request))
            engine_times.append(elapsed)
            assert serialize_yoga_extensions(result).model_dump(mode="json") == want
    start = perf_counter()
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        startup_ms = (perf_counter() - start) * 1000
        first_http, cold_http = timing(
            lambda: client.post("/v1/yogas/extended/evaluate", json=requests[0])
        )
        assert first_http.status_code == 200 and first_http.json() == expected[0]
        times, sizes = [], []
        for _ in range(3):
            for request, want in zip(requests, expected):
                response, elapsed = timing(
                    lambda: client.post("/v1/yogas/extended/evaluate", json=request)
                )
                assert response.status_code == 200 and response.json() == want
                times.append(elapsed)
                sizes.append(len(response.content))
        resource = client.app.state.engine.get_kernel_status()
    receipt = dict(
        python=platform.python_version(),
        platform=platform.platform(),
        corpus=str(source.relative_to(ROOT)),
        corpus_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        cases=len(cases),
        rules_per_request=21,
        profiles=profiles,
        repeats=3,
        first_engine_ms=cold_engine,
        warm_engine=summary(engine_times),
        application_startup_ms=startup_ms,
        first_http_ms=cold_http,
        warm_http=summary(times),
        payload_bytes={"min": min(sizes), "max": max(sizes), "median": median(sizes)},
        resource_status=resource,
        prewarm_enabled=False,
        limitations="In-process ASGI HTTP transport, not a TCP/deployment benchmark. Startup includes normal engine resource discovery; direct evaluation makes no ephemeris calls. First-call timings follow imports. No predictive-accuracy assertion.",
    )
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
