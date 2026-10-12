"""Repeatable bounded-request timings, separate from source/accuracy validation.

Run with project Python and --output PATH. The HTTP app uses a reader-free
factory deliberately; real unpatched startup is covered in server tests.
"""

import argparse
from dataclasses import asdict
from functools import partial
import hashlib
import json
from pathlib import Path
import platform
from statistics import median
from time import perf_counter

from fastapi.testclient import TestClient

from moira import (
    ArgalaReference,
    CharaProjection,
    JaiminiChart,
    assess_argala,
    evaluate_chara_profile,
)
from moira._jaimini_profile_inputs import CLASSICAL, NINE
from moira.jaimini_profile_policy import ARGALA_IDS, CHARA_IDS
import moira_server.app as app_module
from moira_server.config import ServerConfig
from moira_server.services.jaimini_profiles import (
    serialize_argala_assessment,
    serialize_chara_profile,
)


def measure(operation, repeats):
    start = perf_counter()
    first = operation()
    cold = (perf_counter() - start) * 1000
    samples = []
    for _ in range(repeats):
        start = perf_counter()
        result = operation()
        samples.append((perf_counter() - start) * 1000)
        assert result == first, "repeated execution changed its result"
    return first, {
        "first_ms": cold,
        "warm_median_ms": median(samples),
        "warm_max_ms": max(samples),
        "repeats": repeats,
    }


def run(repeats=30):
    classical = JaiminiChart("signs", dict(zip(CLASSICAL, (1, 9, 2, 1, 11, 2, 7))), 7)
    nine = JaiminiChart(
        "sidereal_longitudes",
        {p: 31.0 if i < 4 else 355.0 for i, p in enumerate(NINE)},
        0.0,
    )
    refs = (
        (ArgalaReference("lagna"),)
        + tuple(ArgalaReference("house", h) for h in range(1, 13))
        + tuple(ArgalaReference("planet", p) for p in NINE)
    )
    result = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "scope": "bounded direct arithmetic and reader-free in-process HTTP; performance is not scientific validation",
        "profiles": [],
        "source_sha256": {},
    }
    for path in (
        "moira/chara_profiles.py",
        "moira/argala_assessment.py",
        "moira/_jaimini_profile_inputs.py",
        "moira/jaimini_profile_policy.py",
        "moira_server/services/jaimini_profiles.py",
        "moira_server/models/jaimini_profiles.py",
    ):
        result["source_sha256"][path] = hashlib.sha256(
            Path(path).read_bytes()
        ).hexdigest()
    original = app_module.create_engine
    app_module.create_engine = lambda config: object()
    try:
        with TestClient(
            app_module.create_app(ServerConfig(prewarm_enabled=False))
        ) as client:
            for pid in CHARA_IDS + ARGALA_IDS:
                is_chara = pid in CHARA_IDS
                chart = classical if is_chara else nine
                payload = {
                    "profile_id": pid,
                    "chart": {
                        "basis": chart.basis,
                        "positions": dict(chart.positions),
                        "lagna": chart.lagna,
                    },
                }
                if is_chara:
                    projection = CharaProjection(2451545.0)
                    payload["projection"] = asdict(projection)
                    operation = partial(
                        evaluate_chara_profile,
                        chart,
                        profile_id=pid,
                        projection=projection,
                    )
                    serializer = serialize_chara_profile
                    route = "/v1/jaimini/extended/chara-dasha/profile"
                else:
                    payload["references"] = [asdict(r) for r in refs]
                    operation = partial(
                        assess_argala, chart, profile_id=pid, references=refs
                    )
                    serializer = serialize_argala_assessment
                    route = "/v1/jaimini/extended/argala/assessment"
                engine, timing = measure(operation, repeats)
                expected = serializer(engine).model_dump(mode="json")

                def http():
                    response = client.post(route, json=payload)
                    assert response.status_code == 200, response.text
                    return response.json()

                transported, http_timing = measure(http, repeats)
                assert transported == expected
                result["profiles"].append(
                    {
                        "profile_id": pid,
                        "engine": timing,
                        "http": http_timing,
                        "response_bytes": len(
                            json.dumps(transported, separators=(",", ":")).encode()
                        ),
                        "pair_summaries": 0
                        if is_chara
                        else sum(len(r.pairs) for r in engine.references),
                        "quarter_pairs": 0
                        if is_chara
                        else sum(
                            len(p.quarter_pairs)
                            for r in engine.references
                            for p in r.pairs
                        ),
                    }
                )
    finally:
        app_module.create_engine = original
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for row in receipt["profiles"]:
        print(
            row["profile_id"],
            f"engine median {row['engine']['warm_median_ms']:.3f} ms; HTTP median {row['http']['warm_median_ms']:.3f} ms; {row['response_bytes']} bytes",
        )
