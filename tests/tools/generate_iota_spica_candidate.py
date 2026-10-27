"""Generate and review a separate LOLA candidate tree; never update fixtures.

Run with the project venv: python -m tests.tools.generate_iota_spica_candidate
--output <new-directory>. The destination must not exist. A sibling partial
directory preserves completed profiles if generation fails; only a complete
tree is renamed to the requested destination. Review failures are evidence,
not permission to relax observations, topology contracts, assets or tolerances.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
from uuid import uuid4

import pytest

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira._kernel_paths import find_planetary_kernel
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.lunar_limb import (
    LunarLimbAssetIdentity,
    LunarLimbEventProfile,
    LunarLimbProfileSlice,
    LunarLimbProfileSource,
)
from moira.lunar_occultation_contacts import (
    ContactSearchPolicy,
    lunar_contact_star_at,
    lunar_star_topographic_contacts,
    prepare_lola_rdr_lunar_star_contact_profile,
)
from moira.spk_reader import SpkReader
from tests.integration import test_iota_spica_moira_lola_model as checks
from tests.tools.iota_contact_matching import (
    TimedContactWitness,
    minimum_residual_monotone_same_kind_match,
)

ROOT = Path(__file__).resolve().parents[1]
SECONDS_PER_DAY = 86400.0


def digest(path):
    """Stream identities, including multi-gigabyte planetary kernels."""
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    """Serialize a new evidence artifact in the unpublished candidate tree."""
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")


def log(message):
    print(time.strftime("%H:%M:%S"), message, flush=True)


def load_profile(path):
    """Restore JSON samples through the ordinary immutable profile contracts."""
    data = json.loads(path.read_text(encoding="utf-8"))
    source = data.pop("source")
    source["assets"] = tuple(LunarLimbAssetIdentity(**a) for a in source["assets"])
    data["source"] = LunarLimbProfileSource(**source)
    data["slices"] = tuple(LunarLimbProfileSlice(**s) for s in data["slices"])
    return LunarLimbEventProfile(**data)


def match_contacts(result, observed_site, origin):
    """Keep the original monotone same-kind observation matching policy."""
    observed = tuple(TimedContactWitness(
        c["label"], c["kind"], checks._relative_utc_seconds(c["timestamp_utc"], origin),
    ) for c in observed_site["contacts"])
    model = tuple(TimedContactWitness(
        f"model-{i+1}", c.kind.value, (c.jd_utc-origin)*SECONDS_PER_DAY,
    ) for i, c in enumerate(result.contacts))
    return minimum_residual_monotone_same_kind_match(observed, model)


def refresh_reporting_characterizations(site):
    """Refresh measured labels and allocation inside the unchanged total gate.

    The reserved margin may become negative for an inadmissible candidate;
    the original review then fails. This never widens the total residual,
    solver, height, or contact-topology gates.
    """
    topology = site["topology_characterization"]
    if "required_extra_pair_duration_s" in topology:
        duration_ms = topology["required_extra_pair_duration_s"] * 1000.0
        topology["extra_contact_semantics"] = re.sub(
            r"approximately [0-9.]+ ms wide",
            f"approximately {duration_ms:.3f} ms wide",
            topology["extra_contact_semantics"],
        )
    envelope = site["regression_envelope"]
    budget = envelope["budget_components_s"]
    before = deepcopy(budget)
    budget["frozen_baseline_characterization"] = max(
        budget["frozen_baseline_characterization"],
        math.ceil(site["contact_regression"]["matched_maximum_absolute_residual_s"]*1000.0)/1000.0,
    )
    if budget["frozen_baseline_characterization"] != before["frozen_baseline_characterization"]:
        budget["reserved_reporting_and_model_drift_margin"] = round(
            envelope["maximum_absolute_observed_residual_s"]
            - sum(value for key, value in budget.items()
                  if key != "reserved_reporting_and_model_drift_margin"),
            12,
        )
    return {"previous_budget_components_s": before,
            "candidate_budget_components_s": deepcopy(budget),
            "unchanged_total_gate_s": envelope["maximum_absolute_observed_residual_s"]}


def assert_unchanged_contracts(original, candidate):
    """Permit only derived characterizations; reject any policy/evidence edit."""
    def contracts(payload):
        result = deepcopy(payload)
        for site in result["sites"]:
            site.pop("profile_characterization")
            for key in ("contacts", "matched_maximum_absolute_residual_s",
                        "matched_mean_absolute_residual_s"):
                site["contact_regression"].pop(key)
            site["height_sensitivity"].pop("measured_maximum_matched_feature_shift_s")
            for key in ("second_best_total_absolute_residual_s", "second_best_margin_s",
                        "required_extra_pair_duration_s", "extra_contact_semantics"):
                site["topology_characterization"].pop(key, None)
            budget = site["regression_envelope"]["budget_components_s"]
            for key in ("frozen_baseline_characterization",
                        "reserved_reporting_and_model_drift_margin"):
                budget.pop(key)
        return result
    if contracts(original) != contracts(candidate):
        raise ValueError("Candidate changed an observation, resource identity, topology rule, or gate")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--profiles-from", type=Path,
                        help="Reuse saved profiles only when all recorded input identities match")
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.exists():
        parser.error("output already exists; candidates never overwrite evidence")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name("." + destination.name + ".partial-" + uuid4().hex[:8])
    partial.mkdir()
    log(f"Unpublished candidate tree: {partial}")
    model = checks._load(checks._MODEL_FIXTURE)
    candidate = deepcopy(model)
    observed = checks._load(checks._OBSERVED_FIXTURE)
    protected_paths = (checks._MODEL_FIXTURE, checks._OBSERVED_FIXTURE,
                       ROOT.parent / "moira/corrections.py",
                       ROOT.parent / "moira/occultations.py")
    before = {str(p): digest(p) for p in protected_paths}
    kernel = find_planetary_kernel()
    if kernel is None:
        raise RuntimeError("No admitted planetary kernel is installed")
    manifest = {
        "role": "unpromoted candidate, not new external timing authority",
        "source_head": subprocess.check_output(
            ["git", "-C", str(ROOT.parent), "rev-parse", "HEAD"], text=True).strip(),
        "protected_inputs_sha256": before,
        "kernel": {"path": str(kernel), "bytes": kernel.stat().st_size,
                   "sha256": digest(kernel)},
        "native_sha256": digest(next((ROOT.parent / "moira").glob("_moira_native*.pyd"))),
        "generator_sha256": digest(__file__),
        "unchanged_contracts": ["observations", "asset identities", "search policies",
                                "topology requirements", "tolerances", "height interval"],
    }
    if args.profiles_from:
        previous = json.loads((args.profiles_from / "manifest.json").read_text(encoding="utf-8"))
        for key in ("source_head", "protected_inputs_sha256", "kernel", "native_sha256"):
            if previous[key] != manifest[key]:
                raise ValueError(f"Saved profile inputs differ: {key}")
        manifest["reused_profile_tree"] = str(args.profiles_from.resolve())
    write(partial / "manifest.json", manifest)
    reviews = []
    with SpkReader(kernel) as reader:
        for site in candidate["sites"]:
            site_id = site["site_id"]
            observed_site = checks._site(observed, site["observed_site_id"])
            window = site["search_window_utc"]
            start_utc, end_utc = (jd_from_datetime(checks._utc(window[k]))
                                  for k in ("start", "end"))
            start, end = utc_to_ut1(start_utc), utc_to_ut1(end_utc)
            target = lunar_contact_star_at(
                model["target"]["name"], _ut1_to_ephemeris_tt((start+end)/2, reader))
            lat, lon, height = (site[k] for k in (
                "latitude_deg", "longitude_deg", "observer_elevation_m"))
            log(f"{site_id}: " + ("restoring saved terrain profile" if args.profiles_from
                                    else "building full terrain profile with pinned asset hashes"))
            if args.profiles_from:
                expected_digest = previous.get("profile_files_sha256", {}).get(f"{site_id}-profile.json")
                if expected_digest and digest(args.profiles_from / f"{site_id}-profile.json") != expected_digest:
                    raise ValueError(f"Saved profile bytes changed: {site_id}")
                profile = load_profile(args.profiles_from / f"{site_id}-profile.json")
            else:
                profile = prepare_lola_rdr_lunar_star_contact_profile(
                    target, start, end, lat, lon, observer_elevation_m=height,
                    reader=reader, policy=checks._profile_policy(model),
                    expected_lola_assets=checks._expected_lola_assets(model),
                )
            write(partial / f"{site_id}-profile.json", asdict(profile))
            manifest.setdefault("profile_files_sha256", {})[f"{site_id}-profile.json"] = digest(partial / f"{site_id}-profile.json")
            write(partial / "manifest.json", manifest)
            log(f"{site_id}: profile saved; solving contacts")
            policy = ContactSearchPolicy(**model["contact_search_policy"])
            results = {}
            for elevation in dict.fromkeys((height, *site["height_sensitivity"][
                    "tested_elevation_interval_m"])):
                results[elevation] = lunar_star_topographic_contacts(
                    target, start, end, lat, lon, observer_elevation_m=elevation,
                    profile=replace(profile, observer_elevation_m=elevation),
                    reader=reader, policy=policy,
                )
                write(partial / f"{site_id}-contacts-{elevation}.json", [{
                    "kind": c.kind.value, "jd_ut1": c.jd_ut1, "jd_utc": c.jd_utc,
                    "signed_clearance_deg": c.signed_clearance_deg,
                    "bracket_start_jd_ut1": c.bracket_start_jd_ut1,
                    "bracket_end_jd_ut1": c.bracket_end_jd_ut1,
                } for c in results[elevation].contacts])
                log(f"{site_id}: solved height {elevation} m, "
                    f"{len(results[elevation].contacts)} contacts")
            result = results[height]
            matched = match_contacts(result, observed_site, start_utc)
            # These are measured model characterizations, not topology policy.
            # Keep required counts/kinds/assignments and every tolerance fixed.
            topology = site["topology_characterization"]
            topology["second_best_total_absolute_residual_s"] = matched.second_best_total_absolute_residual_seconds
            topology["second_best_margin_s"] = matched.second_best_margin_seconds
            if matched.extra_model_indices == (0, 1):
                topology["required_extra_pair_duration_s"] = (
                    result.contacts[1].jd_ut1-result.contacts[0].jd_ut1)*SECONDS_PER_DAY
            p = site["profile_characterization"]
            p.update(
                slice_count=len(profile.slices),
                maximum_actual_slice_step_s=max((b.jd_ut1-a.jd_ut1)*SECONDS_PER_DAY
                    for a, b in zip(profile.slices, profile.slices[1:])),
                bin_count_per_slice=len(profile.slices[0].radii_km),
                position_angle_start_unwrapped_deg=profile.slices[0].position_angle_start_unwrapped_deg,
                position_angle_end_unwrapped_deg=profile.slices[0].position_angle_end_unwrapped_deg,
                source_point_counts=[s.source_point_count for s in profile.slices],
                spatial_query_half_width_km=profile.source.spatial_query_half_width_km,
                spatial_query_bounds_moon_xyz_km=profile.source.spatial_query_bounds_moon_xyz_km,
                minimum_radius_km=min(min(s.radii_km) for s in profile.slices),
                maximum_radius_km=max(max(s.radii_km) for s in profile.slices),
                realized_profile_sha256=re.search(r"realized_profile_sha256=([0-9a-f]{64})",
                                                 result.profile_provenance).group(1),
            )
            regression = site["contact_regression"]
            regression["contacts"] = [{
                "model_index": i,
                "kind": c.kind.value,
                "timestamp_utc": c.datetime_utc.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                "observed_match": next((m.observed_label for m in matched.matches
                                         if m.model_index == i), None),
            } for i, c in enumerate(result.contacts)]
            regression["matched_maximum_absolute_residual_s"] = matched.maximum_absolute_residual_seconds
            regression["matched_mean_absolute_residual_s"] = (
                matched.total_absolute_residual_seconds / len(matched.matches))
            shifts = []
            for elevation, alternative in results.items():
                alternative_match = match_contacts(alternative, observed_site, start_utc)
                shifts.extend(abs(alternative.contacts[m.model_index].jd_utc
                    - result.contacts[base.model_index].jd_utc)*SECONDS_PER_DAY
                    for m, base in zip(alternative_match.matches, matched.matches))
            site["height_sensitivity"]["measured_maximum_matched_feature_shift_s"] = max(shifts)
            reporting_characterizations = refresh_reporting_characterizations(site)
            write(partial / "model-candidate.json", candidate)
            uncertainties = {c["label"]: c["uncertainty_95_s"]
                             for c in observed_site["contacts"]}
            observation_comparison = [{
                "observed_label": m.observed_label,
                "signed_residual_s": m.residual_seconds,
                "published_uncertainty_95_s": uncertainties[m.observed_label],
                "outside_published_uncertainty": abs(m.residual_seconds) > uncertainties[m.observed_label],
            } for m in matched.matches]
            receipt = {"site": site_id, "matching": asdict(matched),
                       "maximum_height_shift_s": max(shifts),
                       "contacts": regression["contacts"],
                       "profile_characterization": p,
                       "maximum_solver_clearance_deg": max(abs(c.signed_clearance_deg) for c in result.contacts),
                       "maximum_solver_bracket_seconds": max((c.bracket_end_jd_ut1-c.bracket_start_jd_ut1)*SECONDS_PER_DAY for c in result.contacts),
                       "observation_comparison": observation_comparison,
                       "outside_published_uncertainty_count": sum(c["outside_published_uncertainty"] for c in observation_comparison),
                       "uncertainty_boundary": "A Moira regression-gate pass does not establish agreement within published observation uncertainties.",
                       "reporting_characterizations": reporting_characterizations,
                       "unchanged_contract_review_passed": False}
            # Audit the original integration assertions against these computed
            # results. Reuse terrain/solves in memory, not fixture generations.
            # Fresh STAC mapping and all original resource checks still execute.
            try:
                with pytest.MonkeyPatch.context() as patch:
                    patch.setattr(checks, "_MODEL_FIXTURE", partial / "model-candidate.json")
                    patch.setattr(checks, "prepare_lola_rdr_lunar_star_contact_profile",
                                  lambda *a, **kw: profile)
                    patch.setattr(checks, "lunar_star_topographic_contacts",
                                  lambda *a, **kw: results[kw["observer_elevation_m"]])
                    checks.test_iota_spica_moira_topology_regression(
                        site_id, reader, partial / f"{site_id}-stac-review", patch,
                        lambda key, value: receipt.update(original_assertion_receipt=json.loads(value)),
                    )
                receipt["unchanged_contract_review_passed"] = True
            except Exception:
                receipt["review_failure"] = traceback.format_exc()
            reviews.append(receipt)
            write(partial / f"{site_id}-review.json", receipt)
            log(f"{site_id}: unchanged-contract review "
                f"{'PASS' if receipt['unchanged_contract_review_passed'] else 'FAIL'}; "
                f"max observed residual {matched.maximum_absolute_residual_seconds:.6f} s")
    assert before == {str(p): digest(p) for p in protected_paths}, "input bytes changed during generation"
    assert_unchanged_contracts(model, candidate)
    metadata_review = {"passed": False}
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(checks, "_MODEL_FIXTURE", partial / "model-candidate.json")
            checks.test_iota_spica_moira_model_fixture_keeps_evidence_classes_separate()
        metadata_review["passed"] = True
    except Exception:
        metadata_review["failure"] = traceback.format_exc()
    review = {"passed": metadata_review["passed"] and all(r["unchanged_contract_review_passed"] for r in reviews),
              "metadata_review": metadata_review,
              "sites": reviews, "protected_inputs_unchanged": True,
              "authority_boundary": model["authority_boundary"]}
    write(partial / "review.json", review)
    # A failed scientific review is still a complete, inspectable candidate.
    # Promotion is a separate operation and is never performed by this tool.
    os.rename(partial, destination)
    log(f"Complete candidate tree: {destination}; review={review['passed']}")
    return 0 if review["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
