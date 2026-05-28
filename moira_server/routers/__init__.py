"""Route modules for the Moira REST access surface."""

from .batch import router as batch_router
from .chart import router as chart_router
from .health import router as health_router
from .phenomena import router as phenomena_router
from .positions import router as positions_router
from .relationship import router as relationship_router
from .returns import router as returns_router
from .timelords import router as timelords_router
from .transits import router as transits_router
from .visibility import router as visibility_router

__all__ = [
    "batch_router",
    "chart_router",
    "health_router",
    "phenomena_router",
    "positions_router",
    "relationship_router",
    "returns_router",
    "timelords_router",
    "transits_router",
    "visibility_router",
]
