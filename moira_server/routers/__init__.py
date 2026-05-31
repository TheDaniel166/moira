"""Route modules for the Moira REST access surface."""

from .batch import router as batch_router
from .chart import router as chart_router
from .dasha import router as dasha_router
from .health import router as health_router
from .phenomena import router as phenomena_router
from .positions import router as positions_router
from .progressions import router as progressions_router
from .relationship import router as relationship_router
from .returns import router as returns_router
from .timelords import router as timelords_router
from .transits import router as transits_router
from .asteroids import router as asteroids_router
from .comets import router as comets_router
from .stars import router as stars_router
from .primary_directions import router as primary_directions_router
from .varshaphal import router as varshaphal_router
from .visibility import router as visibility_router

__all__ = [
    "asteroids_router",
    "comets_router",
    "stars_router",
    "batch_router",
    "chart_router",
    "dasha_router",
    "health_router",
    "phenomena_router",
    "positions_router",
    "primary_directions_router",
    "progressions_router",
    "relationship_router",
    "returns_router",
    "timelords_router",
    "transits_router",
    "varshaphal_router",
    "visibility_router",
]
