"""Compatibility module for the shared event-search roundoff owner."""
import sys
from ._event_search import roundoff as _owner

sys.modules[__name__] = _owner
