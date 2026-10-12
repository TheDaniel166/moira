"""Compatibility module for the shared event-search intervals owner."""
import sys
from ._event_search import intervals as _owner

sys.modules[__name__] = _owner
