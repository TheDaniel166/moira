"""Route modules for the Moira REST access surface."""

from .ashtakavarga import router as ashtakavarga_router
from .alternate_dashas import router as alternate_dashas_router
from .antiscia import router as antiscia_router
from .astrocartography import router as astrocartography_router
from .batch import router as batch_router
from .chart import router as chart_router
from .chart_wheel import router as chart_wheel_router
from .dasha import router as dasha_router
from .decans import decanates_router, hermetic_decans_router
from .dignities import router as dignities_router
from .egyptian_bounds import router as egyptian_bounds_router
from .electional import router as electional_router
from .frame_positions import router as frame_positions_router
from .generic_phenomena import router as generic_phenomena_router
from .geodetic import router as geodetic_router
from .galactic import router as galactic_router
from .galactic_houses import router as galactic_houses_router
from .gauquelin import router as gauquelin_router
from .harmograms import router as harmograms_router
from .harmonics import router as harmonics_router
from .health import router as health_router
from .huber import router as huber_router
from .jaimini import router as jaimini_router
from .local_space import router as local_space_router
from .locations import router as locations_router
from .lord_of_the_orb import router as lord_of_the_orb_router
from .lord_of_the_turn import router as lord_of_the_turn_router
from .lots import router as lots_router
from .manazil import router as manazil_router
from .muhurta import router as muhurta_router
from .nodes import router as nodes_router
from .nine_parts import router as nine_parts_router
from .panchanga import router as panchanga_router
from .orbits import router as orbits_router
from .phase import router as phase_router
from .phenomena import router as phenomena_router
from .planetary_hours import router as planetary_hours_router
from .pipeline import router as pipeline_router
from .positions import router as positions_router
from .progressions import router as progressions_router
from .relationship import router as relationship_router
from .returns import router as returns_router
from .shadbala import router as shadbala_router
from .sidereal import router as sidereal_router
from .timelords import router as timelords_router
from .triplicity import router as triplicity_router
from .transits import router as transits_router
from .uranian import router as uranian_router
from .vedic_dignities import router as vedic_dignities_router
from .varga import router as varga_router
from .asteroids import router as asteroids_router
from .comets import router as comets_router
from .stars import router as stars_router
from .primary_directions import router as primary_directions_router
from .varshaphal import router as varshaphal_router
from .visibility import router as visibility_router

__all__ = [
    "ashtakavarga_router",
    "alternate_dashas_router",
    "antiscia_router",
    "astrocartography_router",
    "asteroids_router",
    "comets_router",
    "stars_router",
    "batch_router",
    "chart_router",
    "chart_wheel_router",
    "dasha_router",
    "decanates_router",
    "dignities_router",
    "egyptian_bounds_router",
    "electional_router",
    "frame_positions_router",
    "generic_phenomena_router",
    "geodetic_router",
    "galactic_router",
    "galactic_houses_router",
    "gauquelin_router",
    "harmograms_router",
    "harmonics_router",
    "hermetic_decans_router",
    "health_router",
    "huber_router",
    "jaimini_router",
    "local_space_router",
    "locations_router",
    "lord_of_the_orb_router",
    "lord_of_the_turn_router",
    "lots_router",
    "manazil_router",
    "muhurta_router",
    "nodes_router",
    "nine_parts_router",
    "orbits_router",
    "panchanga_router",
    "phase_router",
    "phenomena_router",
    "planetary_hours_router",
    "pipeline_router",
    "positions_router",
    "primary_directions_router",
    "progressions_router",
    "relationship_router",
    "returns_router",
    "shadbala_router",
    "sidereal_router",
    "timelords_router",
    "triplicity_router",
    "transits_router",
    "uranian_router",
    "vedic_dignities_router",
    "varga_router",
    "varshaphal_router",
    "visibility_router",
]
