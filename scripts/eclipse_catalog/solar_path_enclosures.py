"""Certify central-footprint boundary bands for the solar catalog controls.

This offline validation tool uses NumPy for outward binary64 arithmetic and
SciPy to choose nearby witness points. All conclusions about those witnesses
are checked with enclosing arithmetic. The engine has no such dependencies.
"""

import argparse
from collections import deque
import csv
from dataclasses import dataclass
from fractions import Fraction as F
import gzip
import json
import math
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time

import numpy as np
from scipy.spatial import cKDTree

from _outward_boxes import Box, cross, dot, norm_squared, rational_matrix, stack
from discovery import file_hash

from moira import _eclipse_interval_jets as j
from moira._eclipse_interval import RationalInterval as I, IntervalBudgetError
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_penumbra_exclusion import _cross
from moira._eclipse_solar_scalar_taylor import _smooth_clock_and_polar
from moira._eclipse_stage5_source import prepare_stage5_source
from moira.constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from moira.eclipse import _WGS84_POLAR_RADIUS_KM
from moira._kernel_paths import find_planetary_kernel
from moira.spk_reader import SpkReader

REPO = Path(__file__).resolve().parents[2]
RADII = np.array([EARTH_RADIUS_KM, EARTH_RADIUS_KM, _WGS84_POLAR_RADIUS_KM])
SCALE = F(EARTH_RADIUS_KM)


def shadow_jets(frame, *, keep_shape=False):
    ds, dm = j.norm(frame.sun)[0], j.norm(frame.moon)[0]
    rs, rm = F(SUN_RADIUS_KM), F(MOON_RADIUS_KM)
    if ds.lo - rs - SCALE <= dm.hi + rm + SCALE:
        raise EnclosureUnavailable("disjoint foreground depths not proved")
    delta = j.vector_sub(frame.moon, frame.sun)
    distance = j.norm(delta)
    axis = tuple(j.div(value, distance) for value in delta)
    center = j.dot(frame.moon, axis)
    if -center[0].hi - SCALE <= rm:
        raise EnclosureUnavailable("the forward depth over the whole Earth is not proved")
    sine = j.div(j.constant(rs - rm), distance)
    cosine2 = j.sub(j.constant(1), j.square(sine))
    moment = _cross(frame.moon, axis)
    radius_numerator = j.add(j.constant(rm), j.mul(sine, center))
    if cosine2[0].lo <= 0:
        raise EnclosureUnavailable("external tangent cone angle not proved")
    radius_max = (radius_numerator[0].magnitude + SCALE * sine[0].magnitude) / cosine2[0].sqrt(128).lo
    gap = sum((q[0].square() for q in moment), I.point(0)).sqrt(128) - SCALE - radius_max
    if gap.lo > 0 and not keep_shape:
        return None, gap
    terrestrial_axis = j.matrix_vector(frame.rotation, axis)
    terrestrial_moment = j.matrix_vector(frame.rotation, moment)
    sun_over_radii = tuple(j.scale(value, 1 / F(float(radius)))
                           for value, radius in zip(j.matrix_vector(frame.rotation, frame.sun), RADII))
    return tuple((radius_numerator, sine, cosine2, *terrestrial_axis,
                  *terrestrial_moment, *sun_over_radii)), gap


@dataclass(frozen=True)
class Slabs:
    """Closed time tiles with matching angle, moment and horizon jets."""

    time: Box
    valid: Box
    center: np.ndarray
    whole: Box
    at_center: Box
    slope: Box
    curvature: Box
    smooth: np.ndarray

    def range_for(self, keys, lows, highs):
        whole = self.whole[keys]
        smooth = self.smooth[keys]
        if not np.any(smooth):
            return whole
        offset = Box(lows[:, None], highs[:, None]) - Box.point(self.center[keys, None])
        taylor = self.at_center[keys] + self.slope[keys] * offset + self.curvature[keys] * offset.square()
        return whole.intersect(Box(np.where(smooth[:, None], taylor.lo, whole.lo),
                                   np.where(smooth[:, None], taylor.hi, whole.hi)))


def build_slabs(frame, scope, *, time_width=F(1, 512)):
    pending, active, excluded = [(scope.domain, 0)], [], []
    while pending:
        box, depth = pending.pop()
        try:
            whole = frame(box)
            shape, gap = shadow_jets(whole)
        except (EnclosureUnavailable, IntervalBudgetError):
            whole, shape, gap = None, None, None
        if shape is None and gap is not None:
            excluded.append((box, gap))
            continue
        smooth = whole is not None and whole.continuous and _smooth_clock_and_polar(scope, box)
        if box.width > time_width or whole is None or (not smooth and box.width > F(1, 172800)):
            if depth >= 20:
                raise RuntimeError(f"source or foreground guard failed on {box}")
            middle = box.midpoint
            pending.extend(((I(middle, box.hi), depth + 1), (I(box.lo, middle), depth + 1)))
            continue
        # Midpoint is an exact binary64 value kept in the closed time cell.
        midpoint = float(box.midpoint)
        if smooth:
            point = frame(I.point(F(midpoint)))
            central, _ = shadow_jets(point, keep_shape=True)
        else:
            central = shape
        active.append((box, midpoint, shape, central, smooth))
    combined = sorted([box for box, *_ in active] + [box for box, _ in excluded], key=lambda box: box.lo)
    assert combined[0].lo == scope.domain.lo and combined[-1].hi == scope.domain.hi
    assert all(a.hi == b.lo for a, b in zip(combined, combined[1:]))
    if not active:
        raise RuntimeError("expected a central event")
    outer_time = stack(Box.from_rational(row[0]) for row in active)
    # A proof of inclusion needs an actual time, not a rounded endpoint
    # outside the precise source cell. Inward endpoints are used only to
    # admit witnesses, never to discard the endpoints from exclusion.
    inner_time = Box(np.nextafter(outer_time.lo, np.inf), np.nextafter(outer_time.hi, -np.inf))
    slabs = Slabs(outer_time, inner_time,
                  np.array([row[1] for row in active]),
                  rational_matrix([[v[0] for v in row[2]] for row in active]),
                  rational_matrix([[v[0] for v in row[3]] for row in active]),
                  rational_matrix([[v[1] for v in row[3]] for row in active]),
                  rational_matrix([[v[2] / 2 for v in row[2]] for row in active]),
                  np.array([row[4] for row in active]))
    return slabs, active, excluded


def patch_vector(axis, sign, u0, u1, v0, v1):
    uv = iter(((u0, u1), (v0, v1)))
    coordinates = [((sign, sign) if k == axis else next(uv)) for k in range(3)]
    return Box(np.array([a for a, _ in coordinates]), np.array([b for _, b in coordinates]))


def _geometry(patch, shape):
    scaled = Box.point(RADII) * patch
    length = norm_squared(patch).sqrt()
    r0, sine, cosine2 = shape[:, 0], shape[:, 1], shape[:, 2]
    axis, moment, sun = shape[:, 3:6], shape[:, 6:9], shape[:, 9:12]
    numerator = r0 * length - sine * dot(scaled, axis)
    radial = cross(scaled, axis) - moment * length
    return length, numerator, radial, numerator.square() - cosine2 * norm_squared(radial), dot(sun, patch) - length


def compare(patch, shape, *, centered=False):
    """Evaluate both tangent-cone nappes and the Sun-centre horizon."""
    length, numerator, radial, central, daylight = _geometry(patch, shape)
    undecided = (central.hi >= 0) & (daylight.hi >= 0) & ((central.lo <= 0) | (daylight.lo <= 0))
    if centered and undecided.any():
        shape = shape[undecided]
        r0, sine, cosine2 = shape[:, 0], shape[:, 1], shape[:, 2]
        axis, moment, sun = shape[:, 3:6], shape[:, 6:9], shape[:, 9:12]
        point = Box.point((patch.lo + patch.hi) / 2)
        _, _, _, center_c, center_h = _geometry(point, shape)
        for i in np.flatnonzero(patch.hi > patch.lo):
            diagonal = np.zeros(3)
            diagonal[i] = RADII[i]
            length_rate = patch[i] * length.positive_reciprocal()
            radius_rate = r0 * length_rate - sine * Box.point(RADII[i]) * axis[:, i]
            radial_rate = cross(Box.point(diagonal), axis) - moment * length_rate
            rate_c = Box.point(2) * (numerator[undecided] * radius_rate -
                                    cosine2 * dot(radial[undecided], radial_rate))
            rate_h = sun[:, i] - length_rate
            offset = patch[i] - point[i]
            center_c = center_c + rate_c * offset
            center_h = center_h + rate_h * offset
        c, h = central[undecided].intersect(center_c), daylight[undecided].intersect(center_h)
        central.lo[undecided], central.hi[undecided] = c.lo, c.hi
        daylight.lo[undecided], daylight.hi[undecided] = h.lo, h.hi
    covered = (central.lo > 0) & (daylight.lo > 0)
    excluded = (central.hi < 0) | (daylight.hi < 0)
    return covered, excluded


def refine_patch(patch, slabs, keys, lows, highs, *, time_target, verify_centres=True):
    """Keep every possible time, or prove a common-time interior witness."""
    parameters = patch_vector(*patch)
    centered = max(patch[3] - patch[2], patch[5] - patch[4]) <= 1 / 16
    while keys.size:
        midpoint = (lows + highs) / 2
        shapes = slabs.range_for(keys, lows, highs)
        inside, outside = compare(parameters, shapes, centered=centered)
        admit = (slabs.valid.lo[keys] <= midpoint) & (midpoint <= slabs.valid.hi[keys])
        inside &= admit
        if inside.any():
            pos = int(np.flatnonzero(inside)[0])
            return "inside", midpoint[pos], keys, lows, highs
        keys, lows, highs = keys[~outside], lows[~outside], highs[~outside]
        midpoint = (lows + highs) / 2
        if verify_centres and keys.size:
            sampled = slabs.range_for(keys, midpoint, midpoint)
            admit = (slabs.valid.lo[keys] <= midpoint) & (midpoint <= slabs.valid.hi[keys])
            inside = compare(parameters, sampled, centered=centered)[0] & admit
            if inside.any():
                pos = int(np.flatnonzero(inside)[0])
                return "inside", midpoint[pos], keys, lows, highs
        wide = highs - lows > time_target
        if not np.any(wide):
            break
        keys, lows, highs = (np.concatenate((keys, keys[wide])), np.concatenate((lows, midpoint[wide])),
                             np.concatenate((np.where(wide, midpoint, highs), highs[wide])))
    return ("band" if keys.size else "outside"), None, keys, lows, highs


def classify(slabs, side_km):
    keys = np.arange(slabs.center.size)
    start = (keys, slabs.time.lo, slabs.time.hi)
    queue = deque((((axis, sign, -1., 1., -1., 1.), start) for axis in range(3) for sign in (-1, 1)))
    result = []
    while queue:
        patch, possible = queue.popleft()
        axis, sign, u0, u1, v0, v1 = patch
        side = EARTH_RADIUS_KM * max(u1 - u0, v1 - v0)
        # Time refinement follows the spatial resolution. A failing test
        # retains the entire interval. This heuristic provides no proof.
        target = min(225., max(0.05, side / 16)) / 86400
        state, witness, keys, lows, highs = refine_patch(patch, slabs, *possible, time_target=target)
        if state != "band" or side <= side_km:
            result.append((patch, state, witness, int(keys.size)))
            continue
        u, v = (u0 + u1) / 2, (v0 + v1) / 2
        for a, b in ((u0, u), (u, u1)):
            for c, d in ((v0, v), (v, v1)):
                queue.append(((axis, sign, a, b, c, d), (keys, lows, highs)))
    return result


def distance_receipt(cells):
    """Prove a conservative distance between every retained cell and both sides."""
    by_face = {}
    for patch, state, _, _ in cells:
        axis, sign, u0, u1, v0, v1 = patch
        by_face.setdefault((axis, sign), {}).setdefault(state, []).append((u0, u1, v0, v1))

    def chart_vectors(face, uv):
        axis, sign = face
        xyz = np.empty((len(uv), 3))
        xyz[:, axis] = sign
        xyz[:, [i for i in range(3) if i != axis]] = uv
        return xyz

    def unit_vector_bounds(values):
        return values * norm_squared(values).sqrt()[..., None].positive_reciprocal()

    def normalize_points(values):
        return values / np.linalg.norm(values, axis=1)[:, None]

    worst = {"inside": 0.0, "outside": 0.0}
    missing = {"inside": 0, "outside": 0}
    for side in worst:
        points = []
        for face, groups in by_face.items():
            if groups.get(side):
                boxes = np.asarray(groups[side])
                points.append(chart_vectors(face, (boxes[:, (0, 2)] + boxes[:, (1, 3)]) / 2))
        if not points:
            missing[side] = sum(len(groups.get("band", ())) for groups in by_face.values())
            continue
        points = np.concatenate(points)
        global_tree = cKDTree(normalize_points(points))
        for face, groups in by_face.items():
            if not groups.get("band"):
                continue
            bounds = np.asarray(groups["band"])
            centers = (bounds[:, (0, 2)] + bounds[:, (1, 3)]) / 2
            owner = global_tree.query(normalize_points(chart_vectors(face, centers)))[1]
            p = unit_vector_bounds(Box(chart_vectors(face, bounds[:, (0, 2)]),
                                       chart_vectors(face, bounds[:, (1, 3)])))
            witness_unit = unit_vector_bounds(Box.point(points[owner]))
            # On the scaled sphere the arc is <= (pi/2) times the chord.
            # Scaling back to the ellipsoid increases lengths by at most a.
            distance = (norm_squared(p - witness_unit).sqrt() * Box.point(1.572) * Box.point(EARTH_RADIUS_KM)).hi
            if groups.get(side):
                sources = np.asarray(groups[side])
                witnesses = (sources[:, (0, 2)] + sources[:, (1, 3)]) / 2
                # Large certified rectangles can have a distant centre even
                # where their edges approach the band. Propose nearby
                # rectangles by their edges and centres, then use the
                # closest point inside a proposed certified rectangle.
                sites = np.concatenate([witnesses, *(sources[:, (u, v)]
                    for u in (0, 1) for v in (2, 3))])
                owners = cKDTree(sites).query(centers, k=5)[1] % len(sources)
                boxes = sources[owners]
                candidates = np.clip(centers[:, None, :], boxes[..., (0, 2)], boxes[..., (1, 3)])
                pick = np.argmin(np.sum((candidates - centers[:, None, :])**2, axis=-1), axis=1)
                chosen = candidates[np.arange(len(centers)), pick]
                # For two points in one face the pulled-back straight
                # segment gives the tighter a*||delta uv|| bound.
                nearest_center = witnesses[cKDTree(witnesses).query(centers)[1]]
                for candidates in (chosen, nearest_center):
                    a = Box.point(candidates) - Box(bounds[:, (0, 2)], bounds[:, (1, 3)])
                    same_face = ((a[:, 0].square() + a[:, 1].square()).sqrt() * Box.point(EARTH_RADIUS_KM)).hi
                    distance = np.minimum(distance, same_face)
            worst[side] = max(worst[side], float(np.max(distance)))
    return dict(distance_upper_km=worst, missing_side_witnesses=missing)


def run(reader, lunation, epoch, side_km, time_width, target):
    start = time.monotonic()
    box = I(F(-1, 6), F(1, 6))
    frame, _, scope, stats = prepare_stage5_source(reader, epoch, box, panel_count=8,
                                                  recenter_orientation=False)
    slabs, active, excluded = build_slabs(frame, scope, time_width=time_width)
    print(json.dumps(dict(lunation=lunation, slabs=len(active), excluded=len(excluded),
                          prepared_seconds=time.monotonic()-start, source=stats)), flush=True)
    rows = classify(slabs, side_km)
    counts = {state: sum(row[1] == state for row in rows) for state in ("inside", "outside", "band")}
    area_check = {str((a, s)): sum(F(row[0][3] - row[0][2]) * F(row[0][5] - row[0][4]) for row in rows
                                  if row[0][:2] == (a, s))
                  for a in range(3) for s in (-1, 1)}
    assert set(area_check.values()) == {4} and counts["inside"] > 0 and counts["outside"] > 0
    summary = dict(lunation=lunation, epoch_ut1=epoch, counts=counts, seconds=time.monotonic() - start,
                   **distance_receipt(rows), side_km=side_km, evaluations=stats,
                   max_smooth_tile_seconds=float(time_width*86400),
                   kernel_sha256=scope.records.kernel_sha256_at_reader_open,
                   clock=scope.clock.branch, clock_sha256=scope.clock.source_digests,
                   raw_record_sha256=[record.sha256 for record in scope.records.records],
                   orientation_sha256=scope.orientation_series.sha256, polar_sha256=scope.polar_sha256)
    def rational(interval):
        return [str(interval.lo), str(interval.hi)]
    evidence = dict(summary, cells=rows, time=[str(box.lo), str(box.hi)],
                    excluded_time=[(rational(t), rational(gap)) for t, gap in excluded],
                    active_time=[dict(box=rational(r[0]), mid=r[1], whole=[[rational(v) for v in x] for x in r[2]],
                                      center=[[rational(v) for v in x] for x in r[3]], smooth=bool(r[4]))
                                 for r in active])
    with TemporaryDirectory(dir=target.parent) as staging:
        candidate = Path(staging) / target.name
        with gzip.open(candidate, "xt", encoding="utf-8") as stream:
            json.dump(evidence, stream, allow_nan=False, separators=(",", ":"))
        os.link(candidate, target)
    print(json.dumps(summary), flush=True)


def main():
    os.environ["MOIRA_NO_DOWNLOAD"] = "1"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solar-discovery", type=Path, required=True)
    parser.add_argument("--kernel-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--lunation", action="append", type=int)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--side-km", type=float, default=6.25)
    parser.add_argument("--tile-seconds", type=float, default=168.75)
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards:
        parser.error("shard must be in [0, shards)")
    if not math.isfinite(args.side_km) or not 0 < args.side_km <= float(SCALE):
        parser.error("side-km must be positive and at most one Earth radius")
    if not math.isfinite(args.tile_seconds) or not 0 < args.tile_seconds <= 28800:
        parser.error("tile-seconds must be positive and at most the event window")
    time_width = F(str(args.tile_seconds))/86400
    fixture = REPO / "tests/fixtures/moira_solar_one_limit_92_baseline.json"
    required = {row["lunation_number"] for row in json.loads(fixture.read_bytes())["records"]}
    with args.solar_discovery.open(newline="", encoding="utf-8") as stream:
        cases = {}
        for row in csv.DictReader(stream):
            key = int(row["lunation_number"])
            if key in required:
                if key in cases or row["family"] != "solar":
                    parser.error(f"duplicate or invalid solar catalog row {key}")
                cases[key] = float(row["jd_ut1"])
    if cases.keys() != required:
        parser.error("solar discovery file lacks one or more required lunations")
    selected = sorted(set(args.lunation)) if args.lunation is not None else sorted(cases)
    if not all(key in cases for key in selected):
        parser.error("lunation outside the 92-case corpus")
    ordered = selected[args.shard::args.shards]
    args.out.mkdir(parents=True, exist_ok=True)
    kernel = find_planetary_kernel()
    if kernel is None or file_hash(kernel).lower() != args.kernel_sha256.lower():
        parser.error("planetary kernel is missing or differs from the expected hash")
    with SpkReader(kernel) as source:
        for key in ordered:
            run(source, key, cases[key], args.side_km, time_width, args.out / f"boundary_{key}.json.gz")


if __name__ == "__main__":
    main()
