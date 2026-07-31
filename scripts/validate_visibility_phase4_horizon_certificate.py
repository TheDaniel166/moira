"""Validate the immutable Phase 4 directional-horizon event certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


_EXPECTED_SHA256 = (
    "3baf162ffd5f3e659b1489d60502e409f76c3b20cf6e90ef004eabb06fa029d6"
)
_EXPECTED_BASE_SHA256 = (
    "eacf8c373606c1628cebdd4caa611ece533d368c32c7f86674a13e04a4c13d3e"
)
_DEFAULT_PATH = (
    Path(__file__).resolve().parent
    / "visibility_reference_lab"
    / "phase4_directional_horizon_certificate.json"
)


def _require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValueError(message)


def validate_certificate(path: Path) -> dict[str, Any]:
    """Return a compact receipt after strict identity and semantic checks."""

    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    _require(
        digest == _EXPECTED_SHA256,
        "directional-horizon certificate SHA-256 mismatch",
    )
    document = json.loads(payload)
    _require(
        document.get("schema")
        == (
            "moira.physical-heliacal-visibility-"
            "directional-horizon-certificate/v1"
        ),
        "unexpected directional-horizon certificate schema",
    )
    _require(
        document.get("certificate_id")
        == "physical-heliacal-event-directional-horizon-lipschitz-v1",
        "unexpected directional-horizon certificate id",
    )
    base = document.get("base_crossing_certificate", {})
    _require(
        base.get("source_receipt_sha256") == _EXPECTED_BASE_SHA256,
        "Phase 3 crossing-certificate dependency mismatch",
    )
    _require(
        base.get("apparent_altitude_signal_rate_ceiling_deg_per_day")
        == 1024.0,
        "unexpected apparent-altitude rate ceiling",
    )
    _require(
        base.get("horizontal_azimuth_rate_ceiling_deg_per_day")
        == 1024.0,
        "unexpected horizontal-azimuth rate ceiling",
    )
    profile = document.get("profile_contract", {})
    _require(
        profile.get("interpolation_method_id")
        == "circular_linear_azimuth_v1",
        "unexpected horizon interpolation method",
    )
    _require(
        profile.get("admitted_maximum_gap_deg") == 10.0,
        "unexpected admitted horizon gap",
    )
    _require(
        profile.get("apparent_altitude_domain_deg") == [-5.0, 90.0]
        and profile.get("apparent_altitude_upper_bound_exclusive")
        is True,
        "unexpected admitted horizon-altitude domain",
    )
    derivation = document.get("rate_derivation", {})
    _require(
        derivation.get(
            "admitted_binary_direction_angular_rate_ceiling_deg_per_day"
        )
        == 1024.0,
        "unexpected admitted direction-angular-rate ceiling",
    )
    _require(
        derivation.get("directional_signal")
        == "g = z - r*tan(H(theta))",
        "unexpected directional-horizon signal",
    )
    _require(
        derivation.get("signal_sign_law")
        == (
            "for apparent altitude and H in [-5,90), sign(g) equals "
            "sign(apparent_altitude-H)"
        ),
        "directional signal does not preserve the horizon-crossing law",
    )
    _require(
        derivation.get("zenith_law")
        == "at r=0, g=z and is independent of undefined azimuth",
        "directional signal must remain defined at the zenith",
    )
    _require(
        derivation.get("horizontal_cone_lipschitz_factor_symbol")
        == "K=sqrt(T^2+(Q*S)^2)",
        "unexpected directional-horizon cone factor",
    )
    _require(
        derivation.get("admitted_direction_angular_rate_rad_per_day")
        == "radians(1024)",
        "unexpected direction-angular-rate conversion",
    )
    _require(
        derivation.get("combined_signal_rate_ceiling_per_day")
        == "radians(1024)*(1+K)",
        "unexpected directional-horizon rate formula",
    )
    _require(
        derivation.get("pack_floor_maximum_law")
        == (
            "H_eff=max(profile_horizon,constant_refracted_pack_floor); "
            "its slope is at most S and the constant altitude is included "
            "when bounding T and Q"
        ),
        "unexpected data-pack floor composition law",
    )
    solver = document.get("solver_law", {})
    _require(
        solver.get("certificate_construction")
        == (
            "runtime certificate computes T,Q,S,K for the effective "
            "horizon and substitutes K into radians(1024)*(1+K)"
        ),
        "unexpected runtime certificate construction",
    )
    _require(
        solver.get("unresolved_result")
        == "crossing_completeness_not_certified",
        "unexpected unresolved-crossing policy",
    )
    _require(
        solver.get("dense_sampling_alone_is_a_certificate") is False,
        "dense sampling must not be admitted as a certificate",
    )
    return {
        "status": "accepted",
        "certificate_id": document["certificate_id"],
        "sha256": digest,
        "base_crossing_certificate_sha256": _EXPECTED_BASE_SHA256,
        "maximum_gap_deg": profile["admitted_maximum_gap_deg"],
        "rate_formula": derivation[
            "combined_signal_rate_ceiling_per_day"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "certificate",
        nargs="?",
        type=Path,
        default=_DEFAULT_PATH,
    )
    args = parser.parse_args()
    receipt = validate_certificate(args.certificate.resolve())
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
