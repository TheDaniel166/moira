"""Unit checks for the explicit LOLA regional-query runtime policy."""

import pytest

from moira.lunar_limb import official_lunar_limb_profile_adjustment


@pytest.mark.unit
@pytest.mark.parametrize("query_half_width_km", [0.0, 150.0])
def test_lola_query_half_width_policy_rejects_unvalidated_widths(query_half_width_km: float):
    with pytest.raises(ValueError, match="lola_query_half_width_km must be at least 250.0 km"):
        official_lunar_limb_profile_adjustment(
            2451545.0,
            0.0,
            0.0,
            0.0,
            0.0,
            400000.0,
            lola_query_half_width_km=query_half_width_km,
        )
