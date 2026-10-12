"""Compatibility module for the shared event-search frames owner."""
import sys
from ._event_search import frames as _owner

sys.modules[__name__] = _owner
