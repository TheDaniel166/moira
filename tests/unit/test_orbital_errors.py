"""Public orbital error hierarchy, compatibility, and serialization contracts."""

from __future__ import annotations

import base64
import pickle
from types import SimpleNamespace

import pytest

import moira
from moira import facade, spk_reader
from moira._orbital_errors import (
    OrbitalAmbiguousBodyError,
    OrbitalBodyNotFoundError,
    OrbitalBodyNotLoadedError,
    OrbitalBodyNotSupportedError,
    OrbitalCenterNotAllowedError,
    OrbitalCoverageError,
    OrbitalError,
    OrbitalFrameUnavailableError,
    OrbitalGravityModelError,
    OrbitalInputError,
    OrbitalKernelMissingError,
    OrbitalLegacyBodyNotAllowedError,
    OrbitalPassageUnavailableError,
    OrbitalSearchError,
    OrbitalSourceReceiptError,
    OrbitalStateDegenerateError,
    OrbitalTimeBasisError,
)
from moira.small_body_identity import AmbiguousSmallBodyNameError


_OLD_660_FACADE_PICKLE = (
    "gASVXQAAAAAAAACMDG1vaXJhLmZhY2FkZZSMG01pc3NpbmdFcGhlbWVyaXNLZXJuZWxFcnJv"
    "cpSTlH2UKIwFc3RhdGWUjAdtaXNzaW5nlIwGZGV0YWlslIwHZml4dHVyZZR1hZRSlC4="
)


def test_missing_ephemeris_error_is_one_object_at_all_legacy_paths() -> None:
    assert (
        moira.MissingEphemerisKernelError
        is facade.MissingEphemerisKernelError
        is spk_reader.MissingEphemerisKernelError
    )


def test_old_660_facade_pickle_remains_loadable() -> None:
    restored = pickle.loads(base64.b64decode(_OLD_660_FACADE_PICKLE))
    assert type(restored) is spk_reader.MissingEphemerisKernelError
    assert restored.args == ({"state": "missing", "detail": "fixture"},)


def test_compatibility_mros_are_exactly_ordered() -> None:
    assert OrbitalInputError.__mro__[:3] == (
        OrbitalInputError,
        OrbitalError,
        ValueError,
    )
    assert OrbitalCoverageError.__mro__[:3] == (
        OrbitalCoverageError,
        OrbitalError,
        spk_reader.OutOfRangeError,
    )
    assert OrbitalLegacyBodyNotAllowedError.__mro__[:5] == (
        OrbitalLegacyBodyNotAllowedError,
        OrbitalError,
        KeyError,
        LookupError,
        ValueError,
    )
    assert OrbitalKernelMissingError.__mro__[:5] == (
        OrbitalKernelMissingError,
        OrbitalError,
        spk_reader.MissingKernelError,
        spk_reader.MissingEphemerisKernelError,
        RuntimeError,
    )
    assert OrbitalSearchError.__mro__[:3] == (
        OrbitalSearchError,
        OrbitalError,
        ArithmeticError,
    )
    assert OrbitalPassageUnavailableError.__mro__[:3] == (
        OrbitalPassageUnavailableError,
        OrbitalError,
        ValueError,
    )


def test_ambiguous_body_preserves_small_body_compatibility() -> None:
    candidates = (
        SimpleNamespace(family="asteroid", canonical_name="Echo", naif_id=1),
        SimpleNamespace(family="comet", canonical_name="Echo", naif_id=2),
    )
    error = OrbitalAmbiguousBodyError("Echo", candidates)
    assert isinstance(error, AmbiguousSmallBodyNameError)
    assert error.query == "Echo"
    assert error.candidates == candidates


@pytest.mark.parametrize(
    "error",
    (
        OrbitalInputError("jd_ut", True, ("finite real",)),
        OrbitalBodyNotFoundError("Ceress", ("Ceres",)),
        OrbitalBodyNotSupportedError("Sun", "star", "the center has no orbit"),
        OrbitalCenterNotAllowedError("Moon", "Sun", ("Earth",)),
        OrbitalFrameUnavailableError(
            "TRUE_ECLIPTIC_OF_DATE",
            2300000.0,
            ((2415020.0, 2488070.0),),
        ),
        OrbitalLegacyBodyNotAllowedError(
            "Moon", "orbital_elements_at", ("Mercury",), "osculating_elements"
        ),
        OrbitalBodyNotLoadedError(
            "Ceres", 2000001, "asteroid-wheel", "1", "https://moira-astro.com"
        ),
        OrbitalCoverageError(
            "Ceres", 2000001, 2500000.0, ((2400000.0, 2490000.0),), ("wheel",), True
        ),
        OrbitalKernelMissingError("no active reader"),
        OrbitalGravityModelError("DE430", "DE-0430LE-0430"),
        OrbitalTimeBasisError("UT1_TO_TDB", "DE441", "DE440", 6, "hpiers"),
        OrbitalSourceReceiptError(10, 2000001, "ThirdPartyReader", "source identity"),
        OrbitalStateDegenerateError(
            "rectilinear", "Synthetic", 2451545.0, 1.0, 1.0, 0.0, 1.0e-14
        ),
        OrbitalSearchError(
            (2451545.0, 2451546.0), 96, 20000, 1.0e-8, 1.0e-7,
            "MOIRA_APSIDAL_PASSAGES_V1",
        ),
        OrbitalPassageUnavailableError(
            SimpleNamespace(body=SimpleNamespace(name="Earth")),
            ("APOCENTER",),
        ),
    ),
)
def test_structured_errors_pickle_with_attributes_and_message(error) -> None:
    restored = pickle.loads(pickle.dumps(error, protocol=4))
    assert type(restored) is type(error)
    assert restored.args == error.args
    assert vars(restored) == vars(error)
    assert str(restored) == str(error)


@pytest.mark.parametrize(
    "error",
    (
        OrbitalBodyNotFoundError("missing"),
        OrbitalBodyNotLoadedError("Ceres", 2000001, "wheel", "1", "https://example"),
        OrbitalLegacyBodyNotAllowedError(
            "Moon", "orbital_elements_at", ("Mercury",), "osculating_elements"
        ),
    ),
)
def test_key_compatible_messages_are_not_repr_quoted(error) -> None:
    assert not str(error).startswith(('"', "'"))
