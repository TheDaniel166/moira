"""
Internal annual-lord mixin for the public Moira facade.

These wrappers preserve the public ``Moira`` convenience surface while
delegating specialist annual-lord computation to the owning modules.
"""

from __future__ import annotations

import importlib

_lord_of_the_orb = importlib.import_module("moira.lord_of_the_orb")


class AnnualLordFacadeMixin:
    """RITE: The Annual Lord Witness - the layer that routes the public Moira
    surface to admitted specialist annual-lord techniques without owning their
    doctrine.

THEOREM: Mixin that provides annual-lord convenience wrappers for the public
         ``moira.facade.Moira`` class, delegating each computation to the
         authoritative owning module.

RITE OF PURPOSE:
    AnnualLordFacadeMixin gives Python callers direct access to admitted
    annual-lord surfaces whose public facade shape must preserve caller-owned
    prerequisites. The first admitted surface is Abu Ma'shar's Lord of the Orb.

LAW OF OPERATION:
    Responsibilities:
        - Delegate annual-lord computations to owning modules.
        - Preserve caller-supplied prerequisite truth at the facade boundary.
    Non-responsibilities:
        - Does not derive the birth planetary hour.
        - Does not construct natal or Solar Return charts.
        - Does not expose Lord of the Turn until its facade API is separately
          admitted.
        - Does not return REST transport envelopes.
    Dependencies:
        - moira.lord_of_the_orb
    Structural invariants:
        - Lord of the Orb methods require caller-supplied birth_planet truth.

Canon: Moira Sovereign Facade Architecture; moira.lord_of_the_orb.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._facade_annual_lords.AnnualLordFacadeMixin",
    "risk": "medium",
    "api": {
        "frozen": ["lord_of_orb", "current_lord_of_orb"],
        "internal": []
    },
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """

    def lord_of_orb(self, birth_planet: str, years: int, policy=None):
        """
        Compute Abu Ma'shar's Lord of the Orb from caller-supplied birth-hour ruler truth.
        """
        if policy is None:
            policy = _lord_of_the_orb.DEFAULT_LORD_OF_ORB_POLICY
        return _lord_of_the_orb.lord_of_orb(
            birth_planet,
            years,
            policy=policy,
        )

    def current_lord_of_orb(self, birth_planet: str, age: int, policy=None):
        """
        Return the active Lord of the Orb period from caller-supplied birth-hour ruler truth.
        """
        if policy is None:
            policy = _lord_of_the_orb.DEFAULT_LORD_OF_ORB_POLICY
        return _lord_of_the_orb.current_lord_of_orb(
            birth_planet,
            age,
            policy=policy,
        )
